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
    """Find windows by process name, title, and/or process ID. On macOS results include off-screen windows; is_on_screen reports visibility."""
    return core.windows(name or None, pid or None)

@mcp.tool()
def launch_application(command: list[str], wait: float = 2.0) -> dict:
    """Launch an executable with arguments (no shell), then return its PID and windows. This starts a real application."""
    return core.launch(command, wait)

@mcp.tool()
def show_application(pid: int, window_id: str = '', wait: float = 1.0) -> dict:
    """Request foreground activation for an application. This changes desktop focus; inspect on_screen_verified before assuming it appeared. On macOS activation is app-wide."""
    return core.show_application(pid, window_id or None, wait)

def main():
    mcp.run(transport='stdio')
