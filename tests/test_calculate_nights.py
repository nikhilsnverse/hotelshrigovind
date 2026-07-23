import unittest
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import calculate_nights

class TestCalculateNights(unittest.TestCase):
    def test_examples_from_spec(self):
        ci = datetime(2026, 7, 7, 12, 0)
        co = datetime(2026, 7, 8, 10, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

        co = datetime(2026, 7, 8, 11, 59)
        self.assertEqual(calculate_nights(ci, co), 1)

        co = datetime(2026, 7, 8, 12, 1)
        self.assertEqual(calculate_nights(ci, co), 1)

        co = datetime(2026, 7, 8, 20, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

        co = datetime(2026, 7, 9, 11, 0)
        self.assertEqual(calculate_nights(ci, co), 2)

        co = datetime(2026, 7, 9, 13, 0)
        self.assertEqual(calculate_nights(ci, co), 2)

    def test_same_day_before_noon(self):
        ci = datetime(2026, 7, 10, 9, 0)
        co = datetime(2026, 7, 10, 11, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

    def test_exactly_noon(self):
        ci = datetime(2026, 7, 10, 14, 0)
        co = datetime(2026, 7, 11, 12, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

    def test_one_minute_after_noon(self):
        ci = datetime(2026, 7, 10, 14, 0)
        co = datetime(2026, 7, 11, 12, 1)
        self.assertEqual(calculate_nights(ci, co), 1)

    def test_month_transition(self):
        ci = datetime(2026, 1, 31, 12, 0)
        co = datetime(2026, 2, 1, 13, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

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
        self.assertEqual(calculate_nights(ci, co), 1)

    def test_checkout_before_checkin_returns_one(self):
        ci = datetime(2026, 7, 10, 12, 0)
        co = datetime(2026, 7, 10, 10, 0)
        self.assertEqual(calculate_nights(ci, co), 1)

if __name__ == '__main__':
    unittest.main()
