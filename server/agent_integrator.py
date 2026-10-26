#!/usr/bin/env python3
"""
Ecstasy AI Agent Integrator
Automates 1-click FastMCP server configuration for Cursor, Claude Desktop,
and Antigravity AI coding agents.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class AgentIntegrator:
    """Manages MCP server registration for AI coding IDEs."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).resolve().parent.parent
        self.python_path = sys.executable

    def generate_server_config(self) -> Dict[str, Any]:
        """Generate the standard FastMCP server dictionary for Ecstasy."""
        server_script = str(self.project_root / "server" / "mcp_server.py")
        return {
            "command": self.python_path,
            "args": [server_script],
            "env": {
                "PYTHONPATH": str(self.project_root),
                "PYTHONUNBUFFERED": "1"
            }
        }

    def install_cursor(self, global_install: bool = False) -> str:
        """Install Ecstasy into Cursor IDE MCP configuration."""
        if global_install:
            cursor_dir = Path.home() / ".cursor"
        else:
            cursor_dir = self.project_root / ".cursor"

        cursor_dir.mkdir(parents=True, exist_ok=True)
        config_file = cursor_dir / "mcp.json"

        data: Dict[str, Any] = {"mcpServers": {}}
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                if "mcpServers" not in data:
                    data["mcpServers"] = {}
            except Exception:
                data = {"mcpServers": {}}

        data["mcpServers"]["ecstasy"] = self.generate_server_config()
        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(config_file)

    def install_claude_desktop(self) -> str:
        """Install Ecstasy into Claude Desktop MCP configuration."""
        if sys.platform == "darwin":
            config_dir = Path.home() / "Library" / "Application Support" / "Claude"
        elif sys.platform == "win32":
            appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
            config_dir = Path(appdata) / "Claude"
        else:
            config_dir = Path.home() / ".config" / "Claude"

        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / "claude_desktop_config.json"

        data: Dict[str, Any] = {"mcpServers": {}}
        if config_file.exists():
            try:
                data = json.loads(config_file.read_text(encoding="utf-8"))
                if "mcpServers" not in data:
                    data["mcpServers"] = {}
            except Exception:
                data = {"mcpServers": {}}

        data["mcpServers"]["ecstasy"] = self.generate_server_config()
        config_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return str(config_file)


def configure_agent_mcp(target: str = "cursor", global_install: bool = False, print_only: bool = False) -> Dict[str, Any]:
    integrator = AgentIntegrator()
    config = integrator.generate_server_config()

    if print_only:
        return {"status": "SUCCESS", "config": config}

    if target == "cursor":
        path = integrator.install_cursor(global_install=global_install)
        return {"status": "SUCCESS", "target": "cursor", "path": path, "config": config}
    elif target == "claude":
        path = integrator.install_claude_desktop()
        return {"status": "SUCCESS", "target": "claude_desktop", "path": path, "config": config}
    else:
        return {"status": "ERROR", "message": f"Unsupported target: {target}"}
