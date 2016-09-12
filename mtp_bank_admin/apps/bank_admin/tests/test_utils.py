from unittest import mock
from datetime import date

from django.test import SimpleTestCase

from bank_admin.utils import WorkdayChecker


holidays = {'england-and-wales': {
    'division': 'england-and-wales',
    'events': [
        {'title': 'Boxing Day', 'date': '2016-12-26', 'notes': '', 'bunting': True},
        {'title': 'Christmas Day', 'date': '2016-12-27', 'notes': 'Substitute day', 'bunting': True}]
}}


class WorkdayCheckerTestCase(SimpleTestCase):

    def setUp(self):
        with mock.patch('bank_admin.utils.requests') as mock_requests:
            mock_requests.get().status_code = 200
            mock_requests.get().json.return_value = holidays
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
