import os
import sys
import unittest
from decimal import Decimal
from datetime import datetime, timedelta

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Booking, Room, Customer, Staff, calculate_bill, generate_booking_id, generate_invoice_number


class TestWeddingFeature(unittest.TestCase):
    def setUp(self):
        self.app_ctx = app.app_context()
        self.app_ctx.push()
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
        }
        
        if 'sqlalchemy' in app.extensions:
            try:
                app.extensions['sqlalchemy'].engine.dispose()
            except Exception:
                pass
            del app.extensions['sqlalchemy']
        
        db._engine = None
        db._session_factory = None
        db.init_app(app)
        
        db.drop_all()
        db.create_all()
        db.session.commit()

        self.customer = Customer(
            name='Test Guest',
            phone='9876543210',
            email='test@example.com'
        )
        db.session.add(self.customer)
        db.session.commit()

        self.room1 = Room(
            room_number='W101',
            room_type='deluxe',
            price_per_night=2500,
            status='available',
            floor=1
        )
        self.room2 = Room(
            room_number='W102',
            room_type='deluxe',
            price_per_night=2500,
            status='available',
            floor=1
        )
        self.room3 = Room(
            room_number='W103',
            room_type='suite',
            price_per_night=4000,
            status='available',
            floor=1
        )
        db.session.add_all([self.room1, self.room2, self.room3])
        db.session.commit()

    def tearDown(self):
        db.session.remove()
        if hasattr(db, 'engine') and db.engine:
            try:
                db.engine.dispose()
            except Exception:
                pass
        self.app_ctx.pop()

    def _make_wedding_booking(self, package, stay_duration=1, gst_mode='exclude', gst_rate=5,
                               discount=0, advance=0, custom_room_ids=None):
        b = Booking()
        b.booking_category = 'wedding'
        b.wedding_package = package
        b.stay_duration = stay_duration
        b.gst_mode = gst_mode
        b.gst_rate = Decimal(str(gst_rate))
        b.discount = Decimal(str(discount))
        b.advance_amount = Decimal(str(advance))
        b.extra_person_charges = Decimal('0')
        b.number_of_persons = 1
        if custom_room_ids:
            b.wedding_selected_rooms = ','.join(str(x) for x in custom_room_ids)
            b.wedding_custom_rooms = len(custom_room_ids)
        else:
            b.wedding_selected_rooms = None
            b.wedding_custom_rooms = None
        return b

    def test_all_9_ac_rate(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=2)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('30000'))
        self.assertEqual(data['subtotal'], Decimal('30000'))

    def test_all_rooms_rate(self):
        b = self._make_wedding_booking('all_rooms', stay_duration=1)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('17000'))

    def test_all_rooms_multiple_nights(self):
        b = self._make_wedding_booking('all_rooms', stay_duration=3)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('51000'))

    def test_custom_ac_sum_of_selected_rooms(self):
        b = self._make_wedding_booking('custom_ac', stay_duration=2, custom_room_ids=[self.room1.id, self.room3.id])
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        expected = (Decimal('2500') + Decimal('4000')) * 2
        self.assertEqual(data['base_room_charge'], expected)

    def test_custom_ac_single_room(self):
        b = self._make_wedding_booking('custom_ac', stay_duration=1, custom_room_ids=[self.room2.id])
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('2500'))

    def test_custom_ac_no_rooms_selected_defaults(self):
        b = self._make_wedding_booking('custom_ac', stay_duration=1, custom_room_ids=[])
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('15000'))

    def test_wedding_exclude_gst(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='exclude')
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['gst_amount'], Decimal('750'))
        self.assertEqual(data['total_amount'], Decimal('15750'))

    def test_wedding_include_gst(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='include')
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        expected_gst = Decimal('15000') - (Decimal('15000') * Decimal('100') / Decimal('105'))
        self.assertEqual(data['gst_amount'], expected_gst)
        self.assertEqual(data['total_amount'], Decimal('15000'))

    def test_wedding_no_gst(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='no_gst')
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['gst_amount'], Decimal('0'))
        self.assertEqual(data['total_amount'], Decimal('15000'))

    def test_wedding_with_discount(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='exclude', discount=1000)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['subtotal'], Decimal('14000'))
        self.assertEqual(data['gst_amount'], Decimal('700'))
        self.assertEqual(data['total_amount'], Decimal('14700'))

    def test_wedding_with_advance(self):
        b = self._make_wedding_booking('all_rooms', stay_duration=1, gst_mode='exclude', advance=5000)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['pending_amount'], Decimal('12850'))

    def test_wedding_total_is_whole_rupee_exclude(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='exclude')
        data = calculate_bill(b)
        self.assertEqual(data['total_amount'] % 1, Decimal('0'))

    def test_wedding_total_is_whole_rupee_include(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='include')
        data = calculate_bill(b)
        self.assertEqual(data['total_amount'] % 1, Decimal('0'))

    def test_wedding_round_off_exclude(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='exclude')
        data = calculate_bill(b)
        self.assertEqual(data['round_off'], Decimal('0'))

    def test_wedding_no_extra_person_charges(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1)
        b.extra_person_charges = Decimal('500')
        data = calculate_bill(b)
        self.assertEqual(data['extra_person_charges'], Decimal('0'))
        self.assertEqual(data['base_room_charge'], Decimal('15000'))

    def test_wedding_custom_ac_rate_changes_with_rooms(self):
        b1 = self._make_wedding_booking('custom_ac', stay_duration=1, custom_room_ids=[self.room1.id])
        b2 = self._make_wedding_booking('custom_ac', stay_duration=1, custom_room_ids=[self.room1.id, self.room2.id])
        data1 = calculate_bill(b1)
        data2 = calculate_bill(b2)
        self.assertNotIn('error', data1)
        self.assertNotIn('error', data2)
        self.assertEqual(data1['base_room_charge'], Decimal('2500'))
        self.assertEqual(data2['base_room_charge'], Decimal('5000'))

    def test_wedding_three_nights_all_9_ac(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=3, gst_mode='exclude')
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('45000'))
        self.assertEqual(data['gst_amount'], Decimal('2250'))
        self.assertEqual(data['total_amount'], Decimal('47250'))

    def test_wedding_custom_ac_deluxe_plus_suite(self):
        b = self._make_wedding_booking('custom_ac', stay_duration=2, custom_room_ids=[self.room1.id, self.room3.id])
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('13000'))

    def test_wedding_discount_exceeds_subtotal(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='exclude', discount=20000)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['total_amount'] % 1, Decimal('0'))

    def test_wedding_pending_with_advance(self):
        b = self._make_wedding_booking('all_rooms', stay_duration=2, gst_mode='exclude', advance=5000)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['pending_amount'], Decimal('30700'))

    def test_wedding_invoice_number_generation(self):
        num = generate_invoice_number()
        self.assertIsInstance(num, str)
        self.assertTrue(len(num) >= 1)

    def test_wedding_stay_duration_integer(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=5)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['stay_duration'], 5)

    def test_wedding_package_rate_consistency(self):
        b_all_9 = self._make_wedding_booking('all_9_ac', stay_duration=1)
        b_all = self._make_wedding_booking('all_rooms', stay_duration=1)
        b_custom = self._make_wedding_booking('custom_ac', stay_duration=1, custom_room_ids=[self.room1.id, self.room2.id, self.room3.id])
        data_all_9 = calculate_bill(b_all_9)
        data_all = calculate_bill(b_all)
        data_custom = calculate_bill(b_custom)
        self.assertEqual(data_all_9['base_room_charge'], Decimal('15000'))
        self.assertEqual(data_all['base_room_charge'], Decimal('17000'))
        self.assertEqual(data_custom['base_room_charge'], Decimal('9000'))

    def test_wedding_gst_rate_5_percent(self):
        b = self._make_wedding_booking('all_rooms', stay_duration=2, gst_mode='exclude', gst_rate=5)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        expected_gst = Decimal('17000') * 2 * Decimal('0.05')
        self.assertEqual(data['gst_amount'], expected_gst)

    def test_wedding_gst_rate_18_percent(self):
        b = self._make_wedding_booking('all_rooms', stay_duration=1, gst_mode='exclude', gst_rate=18)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['gst_rate'], Decimal('18'))
        self.assertEqual(data['gst_amount'], Decimal('3060'))

    def test_wedding_with_zero_discount(self):
        b = self._make_wedding_booking('all_9_ac', stay_duration=1, gst_mode='exclude', discount=0)
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['subtotal'], Decimal('15000'))

    def test_wedding_booking_creation_attributes(self):
        booking = Booking(
            booking_id=generate_booking_id(),
            customer_id=self.customer.id,
            room_id=None,
            booking_category='wedding',
            wedding_package='all_9_ac',
            wedding_custom_rooms=None,
            wedding_selected_rooms=None,
            check_in=datetime(2026, 7, 21, 10, 0),
            check_out=datetime(2026, 7, 22, 10, 0),
            actual_check_in=datetime(2026, 7, 21, 10, 0),
            actual_check_out=datetime(2026, 7, 22, 10, 0),
            stay_duration=1,
            billing_mode='24_hours',
            number_of_persons=1,
            gst_mode='exclude',
            room_charge=Decimal('15000'),
            extra_person_charges=Decimal('0'),
            gst_rate=Decimal('5'),
            advance_amount=Decimal('0'),
            discount=Decimal('0'),
            subtotal=Decimal('15000'),
            gst_amount=Decimal('750'),
            total_amount=Decimal('15750'),
            pending_amount=Decimal('15750'),
            status='checked_in',
            checked_in_by=1,
            billing_name='Test Guest',
            company_gst=None,
            company_address=None,
            bill_payer_type='guest',
            payer_name='Test Guest',
            payer_phone='9876543210',
            payer_address=None,
            notes=None,
            purpose_of_visit='Wedding'
        )
        db.session.add(booking)
        db.session.commit()
        fetched = Booking.query.first()
        self.assertEqual(fetched.booking_category, 'wedding')
        self.assertEqual(fetched.wedding_package, 'all_9_ac')
        self.assertIsNone(fetched.room_id)

    def test_wedding_edit_booking_attributes(self):
        booking = Booking(
            booking_id=generate_booking_id(),
            customer_id=self.customer.id,
            room_id=None,
            booking_category='wedding',
            wedding_package='custom_ac',
            wedding_custom_rooms=2,
            wedding_selected_rooms=f'{self.room1.id},{self.room2.id}',
            check_in=datetime(2026, 7, 21, 10, 0),
            check_out=datetime(2026, 7, 22, 10, 0),
            actual_check_in=datetime(2026, 7, 21, 10, 0),
            actual_check_out=datetime(2026, 7, 22, 10, 0),
            stay_duration=1,
            billing_mode='24_hours',
            number_of_persons=1,
            gst_mode='include',
            room_charge=Decimal('5000'),
            extra_person_charges=Decimal('0'),
            gst_rate=Decimal('5'),
            advance_amount=Decimal('0'),
            discount=Decimal('0'),
            subtotal=Decimal('5000'),
            gst_amount=Decimal('238.095'),
            total_amount=Decimal('5000'),
            pending_amount=Decimal('5000'),
            status='checked_in',
            checked_in_by=1,
            billing_name='Test Guest',
            company_gst=None,
            company_address=None,
            bill_payer_type='guest',
            payer_name='Test Guest',
            payer_phone='9876543210',
            payer_address=None,
            notes=None,
            purpose_of_visit='Wedding'
        )
        db.session.add(booking)
        db.session.commit()
        fetched = Booking.query.first()
        self.assertEqual(fetched.wedding_package, 'custom_ac')
        self.assertEqual(fetched.wedding_custom_rooms, 2)
        self.assertEqual(fetched.wedding_selected_rooms, f'{self.room1.id},{self.room2.id}')

    def test_wedding_custom_ac_three_rooms(self):
        b = self._make_wedding_booking('custom_ac', stay_duration=3, custom_room_ids=[self.room1.id, self.room2.id, self.room3.id])
        data = calculate_bill(b)
        self.assertNotIn('error', data)
        self.assertEqual(data['base_room_charge'], Decimal('27000'))


if __name__ == '__main__':
    unittest.main()
