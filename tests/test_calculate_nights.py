import unittest
import os
import sys
from datetime import datetime

# Ensure project root is on sys.path so `app` can be imported when running tests directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import calculate_nights

class TestCalculateNights(unittest.TestCase):
    def test_examples_from_spec(self):
        # 07 Jul 12:00 PM -> 08 Jul 10:00 AM => 1 night
        ci = datetime(2026, 7, 7, 12, 0)
        co = datetime(2026, 7, 8, 10, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

        # 07 Jul 12:00 PM -> 08 Jul 11:59 AM => 1 night
        co = datetime(2026, 7, 8, 11, 59)
        self.assertEqual(calculate_nights(ci, co), 1)

        # 07 Jul 12:00 PM -> 08 Jul 12:01 PM => 2 nights
        co = datetime(2026, 7, 8, 12, 1)
        self.assertEqual(calculate_nights(ci, co), 2)

        # 07 Jul 12:00 PM -> 08 Jul 08:00 PM => 2 nights
        co = datetime(2026, 7, 8, 20, 0)
        self.assertEqual(calculate_nights(ci, co), 2)

        # 07 Jul 12:00 PM -> 09 Jul 11:00 AM => 2 nights
        co = datetime(2026, 7, 9, 11, 0)
        self.assertEqual(calculate_nights(ci, co), 2)

        # 07 Jul 12:00 PM -> 09 Jul 01:00 PM => 3 nights
        co = datetime(2026, 7, 9, 13, 0)
        self.assertEqual(calculate_nights(ci, co), 3)

    def test_same_day_before_noon(self):
        ci = datetime(2026, 7, 10, 9, 0)
        co = datetime(2026, 7, 10, 11, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

    def test_exactly_noon(self):
        ci = datetime(2026, 7, 10, 14, 0)
        co = datetime(2026, 7, 11, 12, 0)
        # checkout exactly at noon should count as 1 night
        self.assertEqual(calculate_nights(ci, co), 1)

    def test_one_minute_after_noon(self):
        ci = datetime(2026, 7, 10, 14, 0)
        co = datetime(2026, 7, 11, 12, 1)
        self.assertEqual(calculate_nights(ci, co), 2)

    def test_month_transition(self):
        ci = datetime(2026, 1, 31, 12, 0)
        co = datetime(2026, 2, 1, 13, 0)
        self.assertEqual(calculate_nights(ci, co), 2)

    def test_24_hour_billing_mode_counts_each_24_hour_block(self):
        ci = datetime(2026, 7, 10, 10, 0)
        co = datetime(2026, 7, 11, 10, 0)
        self.assertEqual(calculate_nights(ci, co, billing_mode='24_hours'), 1)

        co = datetime(2026, 7, 12, 10, 0)
        self.assertEqual(calculate_nights(ci, co, billing_mode='24_hours'), 2)

    def test_leap_year(self):
        ci = datetime(2024, 2, 28, 12, 0)
        co = datetime(2024, 2, 29, 11, 0)
        self.assertEqual(calculate_nights(ci, co), 1)
        co = datetime(2024, 2, 29, 12, 1)
        self.assertEqual(calculate_nights(ci, co), 2)

if __name__ == '__main__':
    unittest.main()
