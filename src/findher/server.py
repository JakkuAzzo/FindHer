"""Local stdio MCP server for Codex, Claude and other MCP clients."""
from mcp.server.fastmcp import FastMCP
from . import core

mcp = FastMCP('FindHer')

@mcp.tool()
def find_processes(name: str = '', pid: int = 0) -> list[dict]:
    """Find running processes by name and/or PID. Empty filters list all processes."""
    return core.processes(name or None, pid or None)

@mcp.tool()
def find_windows(name: str = '', pid: int = 0) -> list[dict]:
    """Find visible windows by process name, title, and/or process ID."""
    return core.windows(name or None, pid or None)

@mcp.tool()
def launch_application(command: list[str], wait: float = 2.0) -> dict:
    """Launch an executable with arguments (no shell), then return its PID and windows. This starts a real application."""
    return core.launch(command, wait)

def main():
    mcp.run(transport='stdio')
