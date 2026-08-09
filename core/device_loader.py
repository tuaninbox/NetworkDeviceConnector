import csv
from typing import List, Dict, Any
from core.nagios import get_hosts_for_hostgroups


def load_devices_from_file(path: str) -> List[Dict]:
    devices = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            devices.append({
                "id": row.get("Host") or row.get("IP"),
                "name": row.get("Host"),
                "ip": row.get("IP"),
                "port": row.get("Port"),
                "location": row.get("Location"),
                "group": row.get("Group"),
                "os": row.get("OS"),
            })
    return devices


async def load_devices(config: Dict[str, Any]) -> List[Dict]:
    """
    Load devices either from Nagios or from CSV file.
    """
    source = config["devices"]["source"]

    if source == "file":
        path = config["devices"]["file_path"]
        return load_devices_from_file(path)

    elif source == "nagios":
        nagios_cfg = config["devices"]["nagios"]
        return await get_hosts_for_hostgroups({"nagios": nagios_cfg})

    else:
        raise ValueError(f"Unknown device source: {source}")
