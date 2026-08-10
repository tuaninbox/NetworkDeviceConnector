from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from deps.auth import get_current_user
from core.logging import log_event
from core.nagios import get_hosts_from_hostgroup
from core.device_loader import load_devices
from models.account import Account
# from models.device import Device
# from schemas.device import DeviceRead, DeviceCreate, DeviceImportItem

router = APIRouter(prefix="/api/devices", tags=["devices"])

@router.get("/")
async def list_devices(
    request: Request,
    current_user: Account = Depends(get_current_user),
):
    """
    Devices are loaded dynamically from Nagios or static file.
    No database model is used.
    """
    cfg = request.app.state.config
    source = cfg["devices"]["source"]

    # Load devices from configured source
    if source in ("file", "nagios"):
        devices = await load_devices(cfg)
        return devices

    raise HTTPException(status_code=500, detail="Invalid device source configuration")

# ---------------------------------------------------------
# NAGIOS SYNC
# ---------------------------------------------------------
@router.post("/nagios/sync")
async def sync_devices_from_nagios(
    hostgroup_name: str,
    current_user: Account = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can sync devices")

    # Load devices directly from Nagios
    devices_data = await get_hosts_from_hostgroup(hostgroup_name)

    # Log sync event (no DB write)
    for d in devices_data:
        log_event(
            "DEVICE_SYNCED_FROM_NAGIOS",
            name=d.get("name"),
            hostgroup=hostgroup_name
        )

    return devices_data


# ---------------------------------------------------------
# IMPORT LOCAL DEVICES 
# ---------------------------------------------------------
@router.post("/import-local")
async def import_local_devices(
    items: list[dict],
    current_user: Account = Depends(get_current_user),
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can import devices")

    # Log import events (no DB write)
    for item in items:
        log_event(
            "DEVICE_IMPORTED_LOCAL",
            name=item.get("name")
        )

    # Just return the items back
    return items