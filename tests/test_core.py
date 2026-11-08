import unittest
from findher.core import parse_wmctrl, filter_records

class CoreTests(unittest.TestCase):
    def test_wmctrl_geometry_and_title(self):
        rows = parse_wmctrl('0x03600007  2 1234 -100 20 800 600 host My Window\n')
        self.assertEqual(rows[0]['window_id'], '0x03600007')
        self.assertEqual(rows[0]['bounds'], {'x': -100, 'y': 20, 'width': 800, 'height': 600})
        self.assertEqual(rows[0]['desktop'], 2)
        self.assertEqual(rows[0]['title'], 'My Window')
    def test_filters_by_name_and_pid(self):
        rows = [{'pid': 42, 'process_name': 'Editor', 'title': 'Hello'}, {'pid': 12, 'process_name': 'Other', 'title': 'world'}]
        self.assertEqual(filter_records(rows, name='EDIT', pid=42), rows[:1])
        self.assertEqual(filter_records(rows, name='hello'), rows[:1])
        self.assertEqual(filter_records(rows, pid=1), [])

class MacWindowTests(unittest.TestCase):
    def test_includes_offscreen_window_and_marks_visibility(self):
        import sys
        from types import SimpleNamespace
        from unittest.mock import patch
        from findher.core import _mac_windows
        all_rows = [
            {'kCGWindowNumber': 77, 'kCGWindowOwnerPID': 960, 'kCGWindowLayer': 0,
             'kCGWindowName': 'Power Automate', 'kCGWindowBounds': {'X': 0, 'Y': 39, 'Width': 1800, 'Height': 1130}},
            {'kCGWindowNumber': 207, 'kCGWindowOwnerPID': 969, 'kCGWindowLayer': 0,
             'kCGWindowBounds': {'X': 10, 'Y': 20, 'Width': 400, 'Height': 300}},
        ]
        q = SimpleNamespace(kCGWindowListOptionAll=0, kCGWindowListOptionOnScreenOnly=1,
                            kCGWindowListExcludeDesktopElements=16, kCGNullWindowID=0,
                            CGWindowListCopyWindowInfo=lambda flags, _: [all_rows[1]] if flags & 1 else all_rows)
        with patch.dict(sys.modules, {'Quartz': q}):
            rows = _mac_windows()
        self.assertEqual([(r['window_id'], r['is_on_screen']) for r in rows], [('77', False), ('207', True)])

class ShowTests(unittest.TestCase):
    def test_rejects_missing_or_invalid_pid(self):
        from findher.core import show_application, FindHerError
        for pid in (0, -1):
            with self.assertRaises(FindHerError):
                show_application(pid)

    def test_reports_visibility_separately_from_activation(self):
        from findher.core import show_application
        from unittest.mock import patch
        with patch('findher.core._activate_application', return_value=True), patch('findher.core.windows', return_value=[{'pid': 42, 'window_id': '77', 'is_on_screen': False}]):
            result = show_application(42, wait=0)
        self.assertTrue(result['activation_requested'])
        self.assertFalse(result['on_screen_verified'])
        self.assertEqual(result['windows'][0]['window_id'], '77')

    def test_visibility_unknown_if_platform_does_not_report_it(self):
        from findher.core import show_application
        from unittest.mock import patch
        with patch('findher.core._activate_application', return_value=True), patch('findher.core.windows', return_value=[{'pid': 42, 'window_id': '1'}]):
            self.assertIsNone(show_application(42, wait=0)['on_screen_verified'])

class HeadlessTests(unittest.TestCase):
    def test_chromium_flags_are_detected_without_exposing_arguments(self):
        from findher.core import headless_status
        self.assertTrue(headless_status('Google Chrome', ['/app/Chrome', '--headless=new', '--user-data-dir=/secret']))
        self.assertTrue(headless_status('chromium', ['/bin/chromium', '--headless']))
        self.assertFalse(headless_status('Google Chrome', ['/app/Chrome', '--profile-directory=Default']))
        self.assertIsNone(headless_status('Google Chrome', None))
        self.assertIsNone(headless_status('other-app', ['other-app', '--headless']))
        self.assertIsNone(headless_status('Google Chrome', []))

    def test_show_rejects_confirmed_headless_browser(self):
        from findher.core import FindHerError, show_application
        from unittest.mock import patch
        with patch('findher.core._process_headless', return_value=True), patch('findher.core._activate_application') as activate:
            with self.assertRaisesRegex(FindHerError, 'headless'):
                show_application(42, wait=0)
            activate.assert_not_called()

    def test_windows_include_headless_status(self):
        from findher.core import windows
        from unittest.mock import patch
        with patch('findher.core.sys.platform', 'darwin'), patch('findher.core._mac_windows', return_value=[{'pid': 42, 'window_id': '77'}]), patch('findher.core.processes', return_value=[{'pid': 42, 'process_name': 'Google Chrome', 'executable': '/Chrome', 'headless_detected': True}]):
            self.assertTrue(windows(pid=42)[0]['headless_detected'])

    def test_process_output_does_not_reveal_private_arguments(self):
        from findher.core import processes
        from unittest.mock import patch
        from types import SimpleNamespace
        proc = SimpleNamespace(info={'pid': 42, 'name': 'Google Chrome', 'exe': '/Chrome', 'cmdline': ['/Chrome', '--headless', '--user-data-dir=/secret']})
        with patch('findher.core.psutil.process_iter', return_value=[proc]):
            result = processes(pid=42)
        self.assertTrue(result[0]['headless_detected'])
        self.assertNotIn('cmdline', result[0])
        self.assertNotIn('/secret', str(result))
