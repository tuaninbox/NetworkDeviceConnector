import httpx
from typing import List, Dict, Any



def derive_os_from_group(group: str) -> str:
    group = group.lower()
    if "ios" in group:
        return "IOS"
    if "nxos" in group:
        return "NXOS"
    return "Unknown"


async def get_hosts_from_hostgroup(
    nagios_host: str,
    nagios_api: str,
    hostgroup: str,
    verify_ssl: bool = False,
) -> List[Dict]:
    url = f"{nagios_host}/nagiosxi/api/v1/objects/host"
    params = {"apikey": nagios_api, "hostgroup_name": hostgroup}

    async with httpx.AsyncClient(verify=verify_ssl) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

    hosts = []
    for host in data.get("host", []):
        hosts.append(
            {
                "id": host.get("host_name") or host.get("address"),
                "name": host.get("host_name"),
                "ip": host.get("address"),
                "port": host.get("port") or "",
                "location": host.get("notes") or "",
                "group": hostgroup,
                "os": derive_os_from_group(hostgroup),
            }
        )
    return hosts


async def get_hosts_for_hostgroups(config: Dict[str, Any]) -> List[Dict]:
    nagios_cfg = config["nagios"]
    nagios_host = nagios_cfg["host"]
    nagios_api = nagios_cfg["api"]
    hostgroups = nagios_cfg["hostgroups"]

    all_hosts = []
    for hg in hostgroups:
        hosts = await get_hosts_from_hostgroup(
            nagios_host=nagios_host,
            nagios_api=nagios_api,
            hostgroup=hg,
            verify_ssl=False,
        )
        all_hosts.extend(hosts)

    return all_hosts


def export_hosts_to_csv(hosts: List[Dict], output_file: str = "nagios_hosts.csv"):
    import csv

    fields = ["Host", "IP", "Port", "Location", "Group", "OS"]

    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(fields)

        for h in hosts:
            writer.writerow([
                h.get("name", ""),
                h.get("ip", ""),
                h.get("port", ""),
                h.get("location", ""),
                h.get("group", ""),
                h.get("os", ""),
            ])

    return output_file
