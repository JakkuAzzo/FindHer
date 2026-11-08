"""Platform adapters and shared process/window discovery."""
from __future__ import annotations
import os
import shutil
import subprocess
import sys
import time
import psutil

class FindHerError(Exception):
    pass

def processes(name=None, pid=None):
    result = []
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            p = proc.info
            if pid is not None and p['pid'] != pid:
                continue
            if name and name.casefold() not in (p['name'] or '').casefold():
                continue
            result.append({'pid': p['pid'], 'process_name': p['name'], 'executable': p['exe']})
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return result

def parse_wmctrl(output):
    result = []
    for line in output.splitlines():
        fields = line.split(None, 8)
        if len(fields) < 8:
            continue
        try:
            wid, desktop, pid, x, y, w, h, _host = fields[:8]
            result.append({'window_id': wid, 'pid': int(pid), 'desktop': int(desktop),
                           'bounds': dict(x=int(x), y=int(y), width=int(w), height=int(h)),
                           'title': fields[8] if len(fields) > 8 else None})
        except ValueError:
            continue
    return result

def filter_records(rows, name=None, pid=None):
    return [row for row in rows if (pid is None or row['pid'] == pid) and
            (not name or name.casefold() in (row.get('process_name') or '').casefold()
             or name.casefold() in (row.get('title') or '').casefold())]

def _mac_windows():
    try:
        import Quartz as q
    except ImportError as exc:
        raise FindHerError('Install the macOS dependencies: reinstall findher-cli with its macOS dependencies') from exc
    infos = q.CGWindowListCopyWindowInfo(q.kCGWindowListOptionAll | q.kCGWindowListExcludeDesktopElements, q.kCGNullWindowID)
    visible = q.CGWindowListCopyWindowInfo(q.kCGWindowListOptionOnScreenOnly | q.kCGWindowListExcludeDesktopElements, q.kCGNullWindowID)
    if infos is None or visible is None:
        raise FindHerError('No macOS window server is available in this session.')
    visible_ids = {item.get('kCGWindowNumber') for item in visible}
    rows = []
    for item in infos:
        if item.get('kCGWindowLayer', 0) != 0:
            continue
        b = item.get('kCGWindowBounds', {})
        rows.append({'window_id': str(item.get('kCGWindowNumber')), 'pid': item.get('kCGWindowOwnerPID'),
                     'title': item.get('kCGWindowName'), 'desktop': None,
                     'is_on_screen': item.get('kCGWindowNumber') in visible_ids,
                     'bounds': {'x': b.get('X'), 'y': b.get('Y'), 'width': b.get('Width'), 'height': b.get('Height')}})
    return rows

def _windows_windows():
    import ctypes
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    try:
        user32.SetProcessDPIAware()
    except AttributeError:
        pass
    callback = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsIconic.argtypes = [wintypes.HWND]
    user32.EnumWindows.argtypes = [callback, wintypes.LPARAM]
    rows = []
    @callback
    def visit(hwnd, _):
        rect = wintypes.RECT()
        pid = wintypes.DWORD()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return True
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        buf = ctypes.create_unicode_buffer(user32.GetWindowTextLengthW(hwnd) + 1)
        user32.GetWindowTextW(hwnd, buf, len(buf))
        rows.append({'window_id': hex(hwnd), 'pid': pid.value, 'title': buf.value or None, 'desktop': None,
                     'is_visible': bool(user32.IsWindowVisible(hwnd)), 'is_minimized': bool(user32.IsIconic(hwnd)),
                     'bounds': {'x': rect.left, 'y': rect.top, 'width': rect.right-rect.left, 'height': rect.bottom-rect.top}})
        return True
    if not user32.EnumWindows(visit, 0):
        raise FindHerError('Windows could not enumerate windows in this session.')
    return rows

def windows(name=None, pid=None):
    if sys.platform == 'darwin':
        rows = _mac_windows()
    elif sys.platform == 'win32':
        rows = _windows_windows()
    elif sys.platform.startswith('linux'):
        if not os.environ.get('DISPLAY'):
            raise FindHerError('No X11 DISPLAY available. Wayland does not provide universal window enumeration; use an X11 session or XWayland (partial results).')
        if not shutil.which('wmctrl'):
            raise FindHerError('Install wmctrl to enumerate X11 windows.')
        try:
            run = subprocess.run(['wmctrl', '-lpG'], capture_output=True, text=True, check=True, timeout=5)
        except (subprocess.SubprocessError, OSError) as exc:
            raise FindHerError(f'Could not enumerate X11 windows: {exc}') from exc
        rows = parse_wmctrl(run.stdout)
    else:
        raise FindHerError(f'Unsupported platform: {sys.platform}')
    lookup = {p['pid']: p for p in processes()}
    for row in rows:
        info = lookup.get(row['pid'], {})
        row['process_name'] = info.get('process_name')
        row['executable'] = info.get('executable')
    return filter_records(rows, name, pid)

def launch(command, wait=2.0):
    if not command or not command[0]:
        raise FindHerError('Provide an executable and optional arguments.')
    if not 0 <= wait <= 30:
        raise FindHerError('Wait must be between 0 and 30 seconds.')
    try:
        child = subprocess.Popen(command, close_fds=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise FindHerError(f'Could not launch {command[0]}: {exc}') from exc
    time.sleep(wait)
    # Some applications delegate to an existing process; never claim ownership of unrelated windows.
    try:
        found = windows(pid=child.pid)
        error = None
    except FindHerError as exc:
        found, error = [], str(exc)
    return {'pid': child.pid, 'running': child.poll() is None, 'windows': found, 'window_error': error}

def _activate_application(pid, window_id=None):
    """Request activation; application APIs can deny or ignore focus changes."""
    if sys.platform == 'darwin':
        if window_id is not None:
            raise FindHerError('macOS activation targets an application, not a specific window; omit --window-id.')
        from AppKit import NSRunningApplication, NSApplicationActivateIgnoringOtherApps
        app = NSRunningApplication.runningApplicationWithProcessIdentifier_(pid)
        if app is None:
            raise FindHerError(f'No running macOS application found for PID {pid}.')
        app.unhide()
        if not app.activateWithOptions_(NSApplicationActivateIgnoringOtherApps):
            raise FindHerError('macOS rejected the activation request.')
        return True
    candidates = windows(pid=pid)
    if window_id is not None:
        try:
            wanted = int(window_id, 0)
            candidates = [row for row in candidates if int(row['window_id'], 0) == wanted]
        except ValueError as exc:
            raise FindHerError('Window ID must be an integer or hexadecimal value.') from exc
    if not candidates:
        raise FindHerError('No matching window found for that PID and window ID.')
    if len(candidates) != 1:
        raise FindHerError('More than one window matches; provide --window-id.')
    wid = candidates[0]['window_id']
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        user32 = ctypes.windll.user32
        user32.IsIconic.argtypes = [wintypes.HWND]
        user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        hwnd = int(wid, 0)
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        elif not candidates[0]['is_visible']:
            user32.ShowWindow(hwnd, 5)  # SW_SHOW
        if not user32.SetForegroundWindow(hwnd):
            raise FindHerError('Windows denied the foreground request; user interaction may be required.')
        return True
    if sys.platform.startswith('linux'):
        try:
            subprocess.run(['wmctrl', '-ia', wid], check=True, capture_output=True, text=True, timeout=5)
        except (subprocess.SubprocessError, OSError) as exc:
            raise FindHerError(f'Could not request X11 window activation: {exc}') from exc
        return True
    raise FindHerError(f'Unsupported platform: {sys.platform}')

def show_application(pid, window_id=None, wait=1.0):
    """Bring an application forward and independently check reported window state."""
    if not isinstance(pid, int) or isinstance(pid, bool) or pid <= 0:
        raise FindHerError('PID must be a positive integer.')
    if not 0 <= wait <= 10:
        raise FindHerError('Wait must be between 0 and 10 seconds.')
    _activate_application(pid, window_id)
    time.sleep(wait)
    try:
        found = windows(pid=pid)
    except FindHerError as exc:
        return {'pid': pid, 'activation_requested': True, 'on_screen_verified': None,
                'windows': [], 'window_error': str(exc)}
    if window_id is not None:
        wanted = int(window_id, 0)
        found = [row for row in found if int(row['window_id'], 0) == wanted]
    states = [row['is_on_screen'] for row in found if isinstance(row.get('is_on_screen'), bool)]
    return {'pid': pid, 'activation_requested': True,
            'on_screen_verified': any(states) if states else None,
            'windows': found, 'window_error': None}
