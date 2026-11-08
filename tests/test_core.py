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
