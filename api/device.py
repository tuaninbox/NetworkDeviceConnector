from fastapi import APIRouter, Body, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from deps.auth import get_current_user_optional
from models.account import Account
from core.audit_logger import log_action
router = APIRouter(prefix="/connector", tags=["Device Connector"])


def get_device(request: Request, device_id: str) -> dict:
    devices = getattr(request.app.state, "devices", []) or []
    for device in devices:
        if device.get("id") == device_id:
            return device
    raise HTTPException(status_code=404, detail="Device not found")


# ---------------------------
# Run a single command
# ---------------------------
@router.post("/{device_id}/run")
async def run_command(
    request: Request,
    device_id: str,
    current_user: Account | None = Depends(get_current_user_optional),
    command: str = Body(..., embed=True)
):
    device = get_device(request, device_id)
    ssh_manager = request.app.state.ssh_manager

    # No command provided
    if not command or not command.strip():
        log_action(
            current_user.username if current_user else None,
            "command_run",
            f"Empty command on {device['name']} - {device['ip']}",
            request,
            category="connector",
        )
        return {
            "ok": False,
            "error": "Input some command"
        }

    # Allowed prefixes
    allowed_prefixes = ["sh", "show", "ping", "dir"]
    if not any(command.lower().startswith(prefix) for prefix in allowed_prefixes):
        log_action(
            current_user.username if current_user else None,
            "command_run",
            f"Rejected command '{command}' on {device['name']} - {device['ip']}",
            request,
            category="connector",
        )
        return {
            "ok": False,
            "error": "Invalid command. Allowed prefixes: sh, show, ping, dir"
        }

    # Block list
    blocked_keywords = [
        "reload", "reboot", "format", "erase", "delete", "shutdown",
        "configure", "conf t", "conf terminal", "debug", "write", "copy",
        "re ", "re-", "wr", "wr mem", "wr memory",
        "shut", "del", "deb", "conf", "no ", "no-", "no_"
    ]
    if any(keyword in command for keyword in blocked_keywords):
        log_action(
            current_user.username if current_user else None,
            "command_run",
            f"Blocked dangerous command '{command}' on {device['name']} - {device['ip']}",
            request,
            category="connector",
        )
        return {
            "ok": False,
            "error": f"Command '{command}' is blocked for safety reasons"
        }

    # Injection prevention
    forbidden_chars = [";", "&", "`", "$(", ">", "<", "&&", "||"]
    if any(char in command for char in forbidden_chars):
        log_action(
            current_user.username if current_user else None,
            "command_run",
            f"Rejected injection attempt '{command}' on {device['name']} - {device['ip']}",
            request,
            category="connector",
        )
        return {
            "ok": False,
            "error": "Invalid command"
        }

    # Try running the command
    try:
        output = await ssh_manager.run_single_command(device, command)
    except ValueError as e:
        # Unsupported OS or platform
        log_action(
            current_user.username if current_user else None,
            "command_run",
            f"Unsupported platform for {device['name']} - {device['os']}",
            request,
            category="connector",
        )
        print(str(e))
        return {
            "ok": False,
            "error": str(e)
        }
    except Exception as e:
        # Any other SSH error
        log_action(
            current_user.username if current_user else None,
            "command_run",
            f"Command '{command}' failed on {device['name']} - {device['ip']}: {str(e)}",
            request,
            category="connector",
        )
        return {
            "ok": False,
            "error": f"Failed to run command: {str(e)}"
        }

    # Success
    log_action(
        current_user.username if current_user else None,
        "command_run",
        f"Command '{command}' executed successfully on {device['name']} - {device['ip']}",
        request,
        category="connector",
    )

    return {
        "ok": True,
        "output": output
    }


# @router.post("/{device_id}/run")
# async def run_command(request: Request, device_id: str, 
#                     current_user: Account | None = Depends(get_current_user_optional),
#                     command: str = Body(..., embed=True)):
#     device = get_device(request, device_id)
#     ssh_manager = request.app.state.ssh_manager

#     # allow prefix
#     allowed_prefixes = ["sh", "show", "ping", "dir"]

#     # Check if command starts with any allowed prefix
#     if not any(command.lower().startswith(prefix) for prefix in allowed_prefixes):
#         log_action(
#             current_user.username,
#             "command_run",
#             f"Command {command} run on {device["name"]} - {device["ip"]} - rejected",
#             request,
#             category="connector",
#         )
#         raise HTTPException(
#             status_code=400,
#             detail=(
#                 "Invalid command. Allowed commands must start with: "
#                 "sh, show, ping, or dir."
#             )
#         )
#     # Block list (dangerous commands)
#     blocked_keywords = [
#         # Full dangerous commands
#         "reload", "reboot", "format", "erase", "delete", "shutdown",
#         "configure", "conf t", "conf terminal", "debug", "write", "copy",

#         # Short versions
#         "re ", "re-", "reboot", "wr", "wr mem", "wr memory",
#         "shut", "del", "deb", "conf", "no ", "no-", "no_"
#     ]

#     if any(keyword in command for keyword in blocked_keywords):
#         log_action(
#             current_user.username,
#             "command_run",
#             f"Command {command} run on {device["name"]} - {device["ip"]} - rejected",
#             request,
#             category="connector",
#         )
#         raise HTTPException(
#             status_code=400,
#             detail=f"Command '{command}' is blocked for safety reasons."
#         )
    
#     # Prevent command injection attempts
#     forbidden_chars = [";", "&", "`", "$(", ">", "<", "&&", "||"]
#     if any(char in command for char in forbidden_chars):
#         log_action(
#             current_user.username,
#             "command_run",
#             f"Command {command} run on {device["name"]} - {device["ip"]} - rejected",
#             request,
#             category="connector",
#         )
#         raise HTTPException(
#             status_code=400,
#             detail="Invalid command."
#         )

#     log_action(
#         current_user,
#         "command_run",
#         f"Command \"{command}\" run on {device["name"]} - {device["ip"]} - successfully",
#         request,
#         category="connector",
#     )
#     output = await ssh_manager.run_single_command(device, command)
#     return {"output": output}


# ---------------------------
# Start interactive session
# ---------------------------
@router.post("/{device_id}/interactive/start")
async def start_interactive(request: Request, device_id: str):
    device = get_device(request, device_id)

    if ssh_manager.get_session(device_id):
        return {"status": "already_active"}

    await ssh_manager.start_session(device)
    return {"status": "started", "device": device_id}


# ---------------------------
# Send command to interactive session
# ---------------------------
@router.post("/{device_id}/interactive/send")
async def interactive_send(device_id: str, command: str = Body(..., embed=True)):
    session = ssh_manager.get_session(device_id)
    if not session:
        raise HTTPException(status_code=400, detail="No active session")

    output = await session.send(command)
    return {"output": output}


# ---------------------------
# Close interactive session
# ---------------------------
@router.post("/{device_id}/interactive/close")
async def close_interactive(device_id: str):
    await ssh_manager.close_session(device_id)
    return {"status": "closed"}


# ============================================================
# 🚀 NEW: WebSocket Interactive Terminal
# ============================================================
@router.websocket("/ws/{device_id}")
async def websocket_terminal(websocket: WebSocket, device_id: str, request: Request):
    await websocket.accept()

    device = get_device(request, device_id)

    # Start or reuse SSH session
    session = ssh_manager.get_session(device_id)
    if not session:
        session = await ssh_manager.start_session(device)

    try:
        await websocket.send_text(
            f"Connected to {device.get('name')} ({device.get('ip')})\n"
        )

        while True:
            data = await websocket.receive_text()

            # Handle terminal resize messages
            if data.startswith("__resize__"):
                _, cols, rows = data.split(":")
                cols = int(cols)
                rows = int(rows)
                await session.channel.request_pty(
                    term_type="xterm",
                    width=cols,
                    height=rows
                )
                continue

            # Allow user to exit
            if data.strip().lower() in ("exit", ":q", "quit"):
                await websocket.send_text("\nSession closed.\n")
                break

            # Send to SSH and stream output back
            output = await session.send(data)

            # Cisco paging detection
            if "--More--" in output:
                await session.channel.write(" ")  # send space
                more_output = await session.channel.read()
                output += more_output

            await websocket.send_text(output)

    except WebSocketDisconnect:
        pass

    finally:
        await ssh_manager.close_session(device_id)
