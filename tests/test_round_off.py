import os
import sys
import unittest
from decimal import Decimal

# Ensure project root is on sys.path so `app` can be imported when running tests directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, round_off_amount, calculate_bill, Booking


class TestRoundOffAmount(unittest.TestCase):
    def test_rounds_half_up(self):
        self.assertEqual(round_off_amount(Decimal('10.5')), Decimal('11'))
        self.assertEqual(round_off_amount(Decimal('10.49')), Decimal('10'))
        self.assertEqual(round_off_amount(Decimal('10.50')), Decimal('11'))
        self.assertEqual(round_off_amount(Decimal('2362.5')), Decimal('2363'))
        self.assertEqual(round_off_amount(Decimal('2362.4')), Decimal('2362'))

    def test_whole_numbers_unchanged(self):
        self.assertEqual(round_off_amount(Decimal('100')), Decimal('100'))
        self.assertEqual(round_off_amount(Decimal('0')), Decimal('0'))

    def test_handles_invalid_input(self):
        self.assertEqual(round_off_amount('not-a-number'), Decimal('0'))
        self.assertEqual(round_off_amount(None), Decimal('0'))

    def test_result_is_whole_rupee(self):
        for val in ['1.01', '999.99', '1500.5', '2500.333', '4000.667']:
            self.assertEqual(round_off_amount(Decimal(val)) % 1, Decimal('0'))


class TestBookingRoundOffProperty(unittest.TestCase):
    def _make_booking(self, total, subtotal, gst_amount, gst_mode):
        b = Booking()
        b.total_amount = Decimal(str(total))
        b.subtotal = Decimal(str(subtotal))
        b.gst_amount = Decimal(str(gst_amount))
        b.gst_mode = gst_mode
        return b

    def test_exclude_mode_round_off(self):
        # subtotal 1000 + gst 50.5 = 1050.5 -> rounded 1051 => round_off +0.5
        b = self._make_booking(total='1051', subtotal='1000', gst_amount='50.5', gst_mode='exclude')
        self.assertEqual(b.round_off, Decimal('0.5'))

    def test_include_mode_round_off(self):
        # include: pre-total = subtotal = 1050.5 -> rounded 1050 => round_off -0.5
        b = self._make_booking(total='1050', subtotal='1050.5', gst_amount='50', gst_mode='include')
        self.assertEqual(b.round_off, Decimal('-0.5'))

    def test_no_round_off_when_already_whole(self):
        b = self._make_booking(total='1050', subtotal='1000', gst_amount='50', gst_mode='exclude')
        self.assertEqual(b.round_off, Decimal('0'))


class TestCalculateBillRounding(unittest.TestCase):
    def _wedding_booking(self, discount, gst_mode='exclude', gst_rate=5):
        b = Booking()
        b.booking_category = 'wedding'
        b.wedding_package = 'all_9_ac'  # 15000 per night
        b.stay_duration = 1
        b.gst_mode = gst_mode
        b.gst_rate = Decimal(str(gst_rate))
        b.discount = Decimal(str(discount))
        b.advance_amount = Decimal('0')
        b.extra_person_charges = Decimal('0')
        return b

    def test_total_is_always_whole_rupee(self):
        with app.app_context():
            # subtotal = 15000 - 14990 = 10; exclude 5% -> gst 0.5 -> 10.5 -> 11
            b = self._wedding_booking(discount=14990)
            data = calculate_bill(b)
            self.assertNotIn('error', data)
            self.assertEqual(data['total_amount'], Decimal('11'))
            self.assertEqual(data['total_amount'] % 1, Decimal('0'))
            self.assertEqual(data['round_off'], Decimal('0.5'))

    def test_pending_matches_rounded_total(self):
        with app.app_context():
            b = self._wedding_booking(discount=14990)
            data = calculate_bill(b)
            self.assertEqual(data['pending_amount'], Decimal('11'))

    def test_various_discounts_produce_whole_totals(self):
        with app.app_context():
            for disc in [0, 1, 7, 13, 99, 123, 14990, 14999]:
                b = self._wedding_booking(discount=disc)
                data = calculate_bill(b)
                self.assertEqual(data['total_amount'] % 1, Decimal('0'),
                                 msg=f'total not whole for discount={disc}: {data["total_amount"]}')


if __name__ == '__main__':
    unittest.main()
