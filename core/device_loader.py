import csv
from typing import List, Dict, Any
from core.nagios import get_hosts_from_all_hostgroups, export_hosts_to_csv


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
    If source is Nagios:
        - Fetch devices from Nagios
        - Save them to the same file_path
        - Reload from file to return final list
    """

    source = config["devices"]["source"]
    # ------------------------------------------------------------
    # Load from file
    # ------------------------------------------------------------
    if source == "file":
        path = config["devices"]["file_path"]
        return load_devices_from_file(path)

    # ------------------------------------------------------------
    # Load from Nagios
    # ------------------------------------------------------------
    elif source == "nagios":
        nagios_cfg = config["devices"]["nagios"]

        # 1. Fetch devices from Nagios
        devices = await get_hosts_from_all_hostgroups(config)

        # 2. Save devices to the same file_path
        path = config["devices"]["file_path"]
        export_hosts_to_csv(devices, path)

        # 3. Reload from file (ensures consistent format)
        return load_devices_from_file(path)

    # ------------------------------------------------------------
    # Unknown source
    # ------------------------------------------------------------
    else:
        raise ValueError(f"Unknown device source: {source}")


async def main():
    from core.config_loader import load_config

    config = load_config()
    print("Loaded config:", config)

    devices = await load_devices(config)
    print("Devices from inventory:", devices)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())