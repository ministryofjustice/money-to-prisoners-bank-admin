from unittest import mock
from datetime import date, datetime

from django.test import SimpleTestCase
from django.utils.timezone import utc

from bank_admin.utils import WorkdayChecker, reconcile_for_date
from . import TEST_HOLIDAYS


@mock.patch('bank_admin.utils.api_client')
class ReconcileForDateTestCase(SimpleTestCase):

    def test_reconciles_midweek(self, mock_api_client):
        start_date, end_date = reconcile_for_date(None, date(2016, 9, 15))

        conn = mock_api_client.get_connection().transactions
        conn.reconcile.post.assert_called_with(
            {'received_at__gte': datetime(2016, 9, 14, 23, 0, tzinfo=utc).isoformat(),
             'received_at__lt': datetime(2016, 9, 15, 23, 0, tzinfo=utc).isoformat()}
        )

        self.assertEqual(start_date, datetime(2016, 9, 14, 23, 0, tzinfo=utc))
        self.assertEqual(end_date, datetime(2016, 9, 15, 23, 0, tzinfo=utc))

    def test_reconciles_weekend(self, mock_api_client):
        start_date, end_date = reconcile_for_date(None, date(2016, 10, 7))

        conn = mock_api_client.get_connection().transactions
        conn.reconcile.post.assert_has_calls([
            mock.call(
                {'received_at__gte': datetime(2016, 10, 6, 23, 0, tzinfo=utc).isoformat(),
                 'received_at__lt': datetime(2016, 10, 7, 23, 0, tzinfo=utc).isoformat()}
            ),
            mock.call(
                {'received_at__gte': datetime(2016, 10, 7, 23, 0, tzinfo=utc).isoformat(),
                 'received_at__lt': datetime(2016, 10, 8, 23, 0, tzinfo=utc).isoformat()}
            ),
            mock.call(
                {'received_at__gte': datetime(2016, 10, 8, 23, 0, tzinfo=utc).isoformat(),
                 'received_at__lt': datetime(2016, 10, 9, 23, 0, tzinfo=utc).isoformat()}
            )
        ])

        self.assertEqual(start_date, datetime(2016, 10, 6, 23, 0, tzinfo=utc))
        self.assertEqual(end_date, datetime(2016, 10, 9, 23, 0, tzinfo=utc))


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

    def test_next_workday_middle_of_week(self):
        next_day = self.checker.get_next_workday(date(2016, 12, 21))
        self.assertEqual(next_day, date(2016, 12, 22))

    def test_next_workday_weekend(self):
        next_day = self.checker.get_next_workday(date(2016, 12, 16))
        self.assertEqual(next_day, date(2016, 12, 19))

    def test_next_workday_bank_holidays(self):
        next_day = self.checker.get_next_workday(date(2016, 12, 23))
        self.assertEqual(next_day, date(2016, 12, 28))

    def test_previous_workday_middle_of_week(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 22))
        self.assertEqual(previous_day, date(2016, 12, 21))

    def test_previous_workday_weekend(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 19))
        self.assertEqual(previous_day, date(2016, 12, 16))

    def test_previous_workday_bank_holidays(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 28))
        self.assertEqual(previous_day, date(2016, 12, 23))
