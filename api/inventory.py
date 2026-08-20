from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user
from core.logging import log_event
from core.device_loader import load_devices_from_file, load_devices
from models.account import Account
from core.permissions import has_permission
from core.audit_logger import log_action
# from models.device import Device
# from schemas.device import DeviceRead, DeviceCreate, DeviceImportItem

router = APIRouter(prefix="/api", tags=["devices"])

@router.get("/devices")
async def list_devices(
    request: Request,
    current_user: Account = Depends(get_current_user),
):
    roles = request.app.state.roles
    if not has_permission(current_user.role, "read_device", roles):
        log_action(
            current_user.username,
            "device_read",
            "Device Read - Permission Denied",
            request,
            category="inventory",
        )
        return {
            "ok": False,
            "error": "Permission denied"
        }
    cfg = request.app.state.config
    source = cfg["devices"]["source"]

    if source not in ("file", "nagios"):
        return {
            "ok": False,
            "error": "Invalid device source configuration",
            "devices": []
        }

    try:
        devices = load_devices_from_file(cfg["devices"]["file_path"])
        return {
            "ok": True,
            "count": len(devices),
            "devices": devices
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Failed to load devices: {str(e)}",
            "devices": []
        }

@router.post("/devices/sync")
async def sync_devices_from_nagios(
    request: Request,
    current_user: Account = Depends(get_current_user),
):
    roles = request.app.state.roles

    # Permission check
    if not has_permission(current_user.role, "sync_nagios", roles):
        log_action(
            current_user.username,
            "device_sync",
            "Nagios Sync - Permission Denied",
            request,
            category="inventory",
        )
        return {
            "ok": False,
            "error": "Permission denied"
        }

    cfg = request.app.state.config

    # Try sync
    try:
        devices = await load_devices(cfg)
    except Exception as e:
        log_action(
            current_user.username,
            "device_sync",
            f"Nagios Sync - Failed: {str(e)}",
            request,
            category="inventory",
        )
        return {
            "ok": False,
            "error": f"Failed to sync devices from Nagios: {str(e)}"
        }

    # Validate result
    if not devices or len(devices) == 0:
        log_action(
            current_user.username,
            "device_sync",
            "Nagios Sync - Returned empty device list",
            request,
            category="inventory",
        )
        return {
            "ok": False,
            "error": "No devices returned from Nagios"
        }

    # Success
    log_action(
        current_user.username,
        "device_sync",
        f"Nagios Sync - Successfully - ({len(devices)} devices)",
        request,
        category="inventory",
    )

    return {
        "ok": True,
        "count": len(devices),
        "devices": devices
    }



# ---------------------------------------------------------
# NAGIOS SYNC
# ---------------------------------------------------------
# @router.post("/nagios/sync")
# async def sync_devices_from_nagios(
#     hostgroup_name: str,
#     current_user: Account = Depends(get_current_user),
# ):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Only admin can sync devices")

#     # Load devices directly from Nagios
#     devices_data = await get_hosts_from_hostgroup(hostgroup_name)

#     # Log sync event (no DB write)
#     for d in devices_data:
#         log_event(
#             "DEVICE_SYNCED_FROM_NAGIOS",
#             name=d.get("name"),
#             hostgroup=hostgroup_name
#         )

#     return devices_data


# # ---------------------------------------------------------
# # IMPORT LOCAL DEVICES 
# # ---------------------------------------------------------
# @router.post("/import-local")
# async def import_local_devices(
#     items: list[dict],
#     current_user: Account = Depends(get_current_user),
# ):
#     if current_user.role != "admin":
#         raise HTTPException(status_code=403, detail="Only admin can import devices")

#     # Log import events (no DB write)
#     for item in items:
#         log_event(
#             "DEVICE_IMPORTED_LOCAL",
#             name=item.get("name")
#         )

#     # Just return the items back
#     return items