# FindHer

FindHer is an open-source terminal tool for finding running applications and their windows. Search by process name or PID, inspect window IDs and positions, or launch an executable. A local MCP server makes the same tools available to Codex, Claude Desktop and Claude Code.

- **Processes:** PID, process name and executable path (when accessible).
- **Windows:** window ID, owning PID, title, position, width and height.
- **Launch:** start an executable and look for windows owned by the new process.
- **Platforms:** macOS, Windows and Linux with X11. See [platform support](#platform-support-and-limitations) for Wayland and other limits.

## Install

You need Git and Python **3.10 or later**. Open Terminal on macOS/Linux or PowerShell on Windows. FindHer runs locally; it does not require an account or API key.

### macOS and Linux

```sh
git clone https://github.com/JakkuAzzo/FindHer.git
cd FindHer
python3 -m venv .venv
source .venv/bin/activate
python -m pip install .
findher --help
```

On Linux, install `wmctrl` to find windows. For example, on Debian or Ubuntu:

```sh
sudo apt install wmctrl
```

Other distributions provide `wmctrl` through their package manager. macOS installs the required Quartz dependency with FindHer.

### Windows (PowerShell)

```powershell
git clone https://github.com/JakkuAzzo/FindHer.git
cd FindHer
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\findher.exe --help
```

Use `.\.venv\Scripts\findher.exe` in place of `findher` in the examples below, or activate the environment with `.\.venv\Scripts\Activate.ps1` and use `findher` directly. The commands assume you are in the cloned FindHer directory when using relative paths.

Keep the repository and its `.venv` in place: the MCP setup below points to the executable inside that environment. To use FindHer in a new macOS/Linux terminal, return to the repository and run `source .venv/bin/activate` again.

## Find a process or window

```sh
# List running processes, or filter by a case-insensitive name substring
findher processes
findher processes --name firefox

# Use a PID from Task Manager, Activity Monitor or another process list
findher processes --pid 1234
findher windows --pid 1234

# Search visible windows by process name or window title
findher windows --name firefox
```

Replace `1234` and `firefox` with your own PID or application name. Combining `--name` and `--pid` requires both to match. A process can have several windows or none; use `processes` to find processes without windows. The `processes --name` filter searches process names, while `windows --name` searches both process names and window titles.

Results are JSON. For example, `findher windows --pid 1234` might return:

```json
[
  {
    "window_id": "207",
    "pid": 1234,
    "title": "My document",
    "desktop": null,
    "bounds": {"x": 100, "y": 80, "width": 920, "height": 600},
    "process_name": "Example",
    "executable": "/path/to/Example"
  }
]
```

The `bounds` describe the **window**, not the monitor's resolution. `desktop` is an X11 workspace number where available; otherwise it is `null`. Titles and executable paths may also be `null`. An empty array (`[]`) means there were no matches. Errors are written to standard error and the command exits with a nonzero status.

## Launch an application

Pass an executable followed by any arguments after `--`:

```sh
findher launch --wait 3 -- /absolute/path/to/executable argument1
```

For example, on Windows PowerShell:

```powershell
.\.venv\Scripts\findher.exe launch --wait 3 -- C:\Windows\System32\notepad.exe
```

`--wait` is a fixed delay in seconds (default 2, maximum 30) before looking for windows. The JSON result contains the spawned `pid`, whether that process is still `running`, any matching `windows`, and `window_error` if window enumeration failed. The tool runs the executable directly; it does not interpret shell operators or expand wildcards. Applications that hand off to an existing instance or a different process may open successfully but return no windows for the spawned PID. Search again by name or by the actual PID if that happens.

## Connect Codex and Claude

The MCP server exposes `find_processes`, `find_windows`, and `launch_application`. It must run on the same computer and in the same graphical session as the applications being inspected. Launching starts a real application, so only connect clients you trust. FindHer is a local stdio server, not a hosted connector.

### Find the executable path

On macOS/Linux, activate the virtual environment, then run:

```sh
command -v findher
```

In Windows PowerShell, from the repository directory, run:

```powershell
(Resolve-Path .\.venv\Scripts\findher.exe).Path
```

Copy the **absolute path** into the configuration below. A path to a virtual environment works only while that environment remains in place.

### Codex

Add the following to `~/.codex/config.toml`, replacing the example path with your own. Preserve any existing configuration:

```toml
[mcp_servers.findher]
command = "/absolute/path/to/findher"
args = ["mcp"]
```

On Windows, use a full path to `findher.exe`; in TOML, a literal single-quoted path avoids escaping backslashes, for example `command = 'C:\Users\you\FindHer\.venv\Scripts\findher.exe'`. Restart Codex, check `codex mcp list`, and ask it to find a running application's window. See the [Codex MCP documentation](https://developers.openai.com/codex/mcp) for current client instructions.

### Claude Desktop

Open the configuration file for your system:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: see [Claude's local MCP guidance](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop) for your installation.

Add `findher` inside the existing `mcpServers` object, preserving other entries. If the file is empty or new, this is a complete example:

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

Replace the example path. On Windows, JSON requires escaped backslashes, for example `"C:\\Users\\you\\FindHer\\.venv\\Scripts\\findher.exe"`. Fully quit and reopen Claude Desktop, then check its local MCP server/connector settings for FindHer and its three tools. Ask Claude to find an application window to try it. See [Claude's setup and troubleshooting guidance](https://support.claude.com/en/articles/10949351-getting-started-with-local-mcp-servers-on-claude-desktop).

### Claude Code

Replace the path below with the absolute path to your installed executable:

```sh
claude mcp add findher -- /absolute/path/to/findher mcp
```

On Windows use the absolute path to `findher.exe` and quote it if it contains spaces. Run `/mcp` inside Claude Code to check the connection and available tools. See the [MCP client setup guide](https://py.sdk.modelcontextprotocol.io/get-started/real-host/) for the current Claude Code instructions.

## Platform support and limitations

- **macOS:** Lists on-screen, normal-layer windows in the current graphical session. macOS may omit titles without Screen Recording permission for the terminal or MCP host. Space numbers are not exposed. Bounds are in screen points.
- **Windows:** Lists visible top-level windows in the current session using DPI-aware screen coordinates. Workspace numbers are not reported. Protected or higher-privilege processes may hide metadata.
- **Linux:** Uses `wmctrl` and an EWMH-compatible X11 window manager. On Wayland, XWayland may expose only X11 windows; native Wayland windows are not universally discoverable. Without an X11 display, window enumeration reports an error, while process listing can still work.

Coordinates are platform-provided and are not necessarily physical pixels. Negative positions can occur with multiple monitors. Window IDs and PIDs can be reused, and windows can disappear between queries. FindHer does not capture screenshots or read window contents.

The portable test suite runs on all three operating systems in CI. Live graphical discovery and launch have been exercised on macOS; Windows and Linux graphical-desktop behavior still needs testing on target desktops.

## Troubleshooting

- **`findher` is not found:** Activate the virtual environment or call its executable by absolute path. On Windows use `.venv\Scripts\findher.exe`.
- **No windows for a PID:** Confirm the process still exists, has a visible window and is in the same graphical session. Some apps use a different process for their windows.
- **Missing title or executable:** The OS may restrict access. On macOS, check Screen Recording permissions for the app hosting FindHer if window titles are missing.
- **Linux reports no X11 display or `wmctrl`:** Install `wmctrl` and use an X11 session. A Wayland session may expose only XWayland windows.
- **MCP server does not connect:** Verify the executable path, run `findher --help` from that environment, check the client logs and restart the client after configuration changes. GUI clients may not inherit the same environment variables as your terminal; Linux clients need access to the graphical session's display.

## Development and tests

From a virtual environment in the repository:

```sh
python -m pip install .
python -m unittest discover -s tests
```

Contributions and issue reports are welcome. FindHer is released under the [MIT License](LICENSE).
