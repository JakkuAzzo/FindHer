# FindHer

Find running processes and their desktop windows from a terminal, Codex or Claude. FindHer reports process IDs, window IDs, window position and size, and executable paths where the operating system permits access. It can also launch an executable and inspect windows belonging to the launched process.

## Install

Requires Python 3.10 or newer. Clone this repository, then:

```sh
python -m pip install .
```

On Linux with X11, install `wmctrl` using your distribution's package manager. On macOS the Quartz dependency is installed automatically.

## Use

```sh
findher processes --name firefox
findher processes --pid 1234
findher windows --name firefox
findher windows --pid 1234
findher launch --wait 3 -- /absolute/path/to/application arg1
```

Commands return JSON; an empty array means no matches. Window records contain `window_id`, `pid`, `process_name`, `executable`, `title`, `desktop`, and `bounds` (`x`, `y`, `width`, `height`). `desktop` is an X11 workspace number when available, and `null` otherwise. Coordinates and dimensions are supplied by the platform, not necessarily physical pixels: macOS uses screen points, Windows uses DPI-aware screen coordinates, and X11 uses its root-window coordinate system. Negative positions can occur on multiple monitors. Width and height describe the **window**, not the display resolution.

`launch` takes an executable and arguments directly, with no shell expansion. Its PID is the spawned process; applications that delegate to an existing instance or another process may yield no windows. `window_error` reports an enumeration failure separately from the launch result. `--wait` is a fixed delay from 0 to 30 seconds. An application can take longer to appear.

## Codex and Claude

FindHer provides a local MCP server with `find_processes`, `find_windows`, and `launch_application`. Install FindHer on the same machine and in the same graphical session as the applications you want to inspect. Use the absolute path to the installed `findher` executable so your client can find it. Launching is a real action; only connect clients you trust.

Codex: add this to `~/.codex/config.toml`:

```toml
[mcp_servers.findher]
command = "/absolute/path/to/findher"
args = ["mcp"]
```

Claude Desktop: add this entry to your MCP configuration:

```json
{
  "mcpServers": {
    "findher": {
      "command": "/absolute/path/to/findher",
      "args": ["mcp"]
    }
  }
}
```

On Windows, use the full path to `findher.exe` and escape backslashes in JSON. Restart the client after updating its configuration. Claude Code also supports configuring a stdio MCP server; see its current documentation for the configuration location.

## Platform boundaries

- **macOS:** Enumerates on-screen, normal-layer windows in the current graphical session. macOS may omit window titles without Screen Recording permission for the terminal or MCP host. Space numbers are not exposed. Bounds are points.
- **Windows:** Enumerates visible top-level windows in the current session. Desktop/workspace numbers are not reported. Some protected or higher-privilege processes may hide metadata.
- **Linux:** Uses `wmctrl` and an EWMH-compatible X11 window manager. Under Wayland, XWayland may expose only X11 windows; native Wayland windows are not universally discoverable. Without X11, window enumeration returns an explicit error. Process listing still works.

A window can disappear between enumeration and inspection. PIDs and window IDs can be reused, and process metadata may be unavailable due to permissions. FindHer does not read the contents of windows or capture screenshots. Windows and Linux graphical integrations need testing on target desktops; CI runs portable tests on all three operating systems.

## Development

```sh
python -m pip install -e .
python -m unittest discover -s tests
```

MIT licensed; contributions and issue reports are welcome.
