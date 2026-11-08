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
