import os
from typing import Dict

from src.config.settings import config


class QuickFIXConfigManager:
    @staticmethod
    def update_config_file(config_file: str, connection_type: str) -> str:
        """Update configuration file with runtime settings"""

        # Read the base configuration
        with open(config_file, "r") as f:
            content = f.read()

        # Get port based on connection type
        port = config.fix.trade_port if connection_type == "trade" else config.fix.feed_port

        # Add dynamic settings
        dynamic_settings = f"""SocketConnectHost={config.fix.host}
SocketConnectPort={port}
SenderCompID={config.fix.sender_comp_id}
TargetCompID={config.fix.target_comp_id}"""

        # Insert dynamic settings after [DEFAULT] section
        lines = content.split("\n")
        result_lines = []
        in_default_section = False

        for line in lines:
            result_lines.append(line)
            if line.strip() == "[DEFAULT]":
                in_default_section = True
            elif in_default_section and line.strip().startswith("["):
                # We've moved to the next section, insert our dynamic settings before it
                result_lines.extend(dynamic_settings.strip().split("\n"))
                in_default_section = False

        # If we're still in DEFAULT section at the end, add settings
        if in_default_section:
            result_lines.extend(dynamic_settings.strip().split("\n"))

        # Write to a temporary config file
        temp_config_file = f"{config_file}.runtime"
        with open(temp_config_file, "w") as f:
            f.write("\n".join(result_lines))

        return temp_config_file

    @staticmethod
    def cleanup_temp_config(config_file: str):
        """Clean up temporary configuration file"""
        if os.path.exists(config_file):
            try:
                os.remove(config_file)
            except Exception:
                pass
