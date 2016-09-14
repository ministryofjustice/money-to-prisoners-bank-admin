from unittest import mock
from datetime import date

from django.test import SimpleTestCase

from bank_admin.utils import WorkdayChecker
from . import TEST_HOLIDAYS


class WorkdayCheckerTestCase(SimpleTestCase):

    def setUp(self):
        with mock.patch('bank_admin.utils.requests') as mock_requests:
            mock_requests.get().status_code = 200
            mock_requests.get().json.return_value = TEST_HOLIDAYS
            self.checker = WorkdayChecker()

    def test_christmas_is_not_workday(self):
        self.assertFalse(self.checker.is_workday(date(2016, 12, 27)))

    def test_weekend_is_not_workday(self):
        self.assertFalse(self.checker.is_workday(date(2016, 12, 17)))

    def test_weekday_is_workday(self):
        self.assertTrue(self.checker.is_workday(date(2016, 12, 21)))

    def test_previous_workday_middle_of_week(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 22))
        self.assertEqual(previous_day, date(2016, 12, 21))

    def test_previous_workday_weekend(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 19))
        self.assertEqual(previous_day, date(2016, 12, 16))

    def test_previous_workday_bank_holidays(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 28))
        self.assertEqual(previous_day, date(2016, 12, 23))

    def test_reconciliation_bounds_middle_of_week(self):
        start_date, end_date = self.checker.get_reconciliation_period_bounds(date(2016, 12, 22))
        self.assertEqual(start_date, date(2016, 12, 22))
        self.assertEqual(end_date, date(2016, 12, 23))

    def test_reconciliation_bounds_weekend(self):
        start_date, end_date = self.checker.get_reconciliation_period_bounds(date(2016, 12, 19))
        self.assertEqual(start_date, date(2016, 12, 17))
        self.assertEqual(end_date, date(2016, 12, 20))

    def test_reconciliation_bounds_bank_holidays(self):
        start_date, end_date = self.checker.get_reconciliation_period_bounds(date(2016, 12, 28))
        self.assertEqual(start_date, date(2016, 12, 24))
        self.assertEqual(end_date, date(2016, 12, 29))
