import os
import yaml
import configparser
from pathlib import Path
from typing import Dict, Any

def load_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load credentials from either YAML or INI-style credential files.

    Supports formats:

    --- YAML ---
    tacacs:
      username: admin
      password: cisco

    --- INI ---
    [tacacs]
    username=admin
    password=cisco

    Returns normalized dict:
    {
        "tacacs": {"username": "admin", "password": "cisco"},
        "nagios": {"apihost": "...", "apikey": "..."}
    }
    """

    # Get credential file path from config
    cred_section = config.get("credentials", {})
    cred_file = cred_section.get("file")

    if not cred_file:
        raise ValueError("credentials.file is missing in config/config.yaml")

    # Support both "credentials" and "credentials.yaml"
    possible_paths = [
        Path(f"{cred_file}.yaml"),
        Path(f"{cred_file}.yml"),
        Path(f"{cred_file}.ini"),
        Path(f"{cred_file}.cfg"),
        Path(cred_file)
    ]

    cred_path = next((p for p in possible_paths if p.exists()), None)

    if not cred_path:
        raise FileNotFoundError(f"Credential file not found: {cred_file}")

    # --- Detect format ---
    ext = cred_path.suffix.lower()

    normalized: Dict[str, Dict[str, Any]] = {}

    if ext in [".yaml", ".yml"]:
        # YAML loader
        with open(cred_path, "r") as f:
            raw = yaml.safe_load(f) or {}

        for section, items in raw.items():
            if isinstance(items, list):
                merged = {}
                for entry in items:
                    if isinstance(entry, dict):
                        merged.update(entry)
                normalized[section] = merged
            elif isinstance(items, dict):
                normalized[section] = items
            else:
                normalized[section] = {}

    else:
        # INI loader
        parser = configparser.ConfigParser()
        parser.read(cred_path)

        for section in parser.sections():
            normalized[section] = dict(parser.items(section))

    return normalized


def load_credentials_yaml(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Load credentials from the credentials file defined in config/config.yaml.

    Supports credential files structured like:

    tacacs:
      - username: admin
      - password: cisco

    nagios:
      - apihost: 10.1.1.1
      - apikey: ABC123

    Returns a normalized dict:

    {
        "tacacs": {"username": "admin", "password": "cisco"},
        "nagios": {"apihost": "...", "apikey": "..."}
    }
    """

    # Get credential file path from config
    cred_section = config.get("credentials", {})
    cred_file = cred_section.get("file")

    if not cred_file:
        raise ValueError("credentials.file is missing in config/config.yaml")

    # Support both "credentials" and "credentials.yaml"
    possible_paths = [
        Path(f"{cred_file}.yaml"),
        Path(f"{cred_file}.yml"),
        Path(cred_file)
    ]

    cred_path = next((p for p in possible_paths if p.exists()), None)

    if not cred_path:
        raise FileNotFoundError(f"Credential file not found: {cred_file}")

    # Load YAML
    with open(cred_path, "r") as f:
        raw = yaml.safe_load(f) or {}

    normalized: Dict[str, Dict[str, Any]] = {}

    # Normalize list-style credentials into dicts
    for section, items in raw.items():
        if isinstance(items, list):
            # Convert list of {key: value} into a single dict
            merged = {}
            for entry in items:
                if isinstance(entry, dict):
                    merged.update(entry)
            normalized[section] = merged
        elif isinstance(items, dict):
            normalized[section] = items
        else:
            normalized[section] = {}

    return normalized

# Usage:
# from core.config_loader import load_config
# from core.credential_loader import load_credentials

# config = load_config()
# creds = load_credentials(config)

# tacacs_user = creds["tacacs"]["username"]
# tacacs_pass = creds["tacacs"]["password"]

# nagios_host = creds["nagios"]["apihost"]
# nagios_key  = creds["nagios"]["apikey"]
