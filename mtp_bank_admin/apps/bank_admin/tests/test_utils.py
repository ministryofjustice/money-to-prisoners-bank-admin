from datetime import date, datetime
from unittest import mock

from django.test import SimpleTestCase
from django.utils.timezone import utc
from mtp_common.auth.test_utils import generate_tokens
import responses

from bank_admin.utils import WorkdayChecker, reconcile_for_date
from . import mock_bank_holidays, api_url, assert_called_with


class ReconcileForDateTestCase(SimpleTestCase):

    def setUp(self):
        self.request = mock.MagicMock(
            user=mock.MagicMock(
                token=generate_tokens()
            )
        )

    @responses.activate
    def test_reconciles_midweek(self):
        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )

        start_date, end_date = reconcile_for_date(self.request, date(2016, 9, 15))

        assert_called_with(
            self, api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 9, 15, 0, 0, tzinfo=utc).isoformat(),
                'received_at__lt': datetime(2016, 9, 16, 0, 0, tzinfo=utc).isoformat()
            }
        )

        self.assertEqual(start_date, datetime(2016, 9, 15, 0, 0, tzinfo=utc))
        self.assertEqual(end_date, datetime(2016, 9, 16, 0, 0, tzinfo=utc))

    @responses.activate
    def test_reconciles_weekend(self):
        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )

        start_date, end_date = reconcile_for_date(self.request, date(2016, 10, 7))

        assert_called_with(
            self, api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 10, 7, 0, 0, tzinfo=utc).isoformat(),
                'received_at__lt': datetime(2016, 10, 8, 0, 0, tzinfo=utc).isoformat()
            }
        )
        assert_called_with(
            self, api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 10, 8, 0, 0, tzinfo=utc).isoformat(),
                'received_at__lt': datetime(2016, 10, 9, 0, 0, tzinfo=utc).isoformat()
            }
        )
        assert_called_with(
            self, api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 10, 9, 0, 0, tzinfo=utc).isoformat(),
                'received_at__lt': datetime(2016, 10, 10, 0, 0, tzinfo=utc).isoformat()
            }
        )

        self.assertEqual(start_date, datetime(2016, 10, 7, 0, 0, tzinfo=utc))
        self.assertEqual(end_date, datetime(2016, 10, 10, 0, 0, tzinfo=utc))


class WorkdayCheckerTestCase(SimpleTestCase):

    def setUp(self):
        mock_bank_holidays()
        self.checker = WorkdayChecker()

    @responses.activate
    def test_christmas_is_not_workday(self):
        self.assertFalse(self.checker.is_workday(date(2016, 12, 27)))

    @responses.activate
    def test_weekend_is_not_workday(self):
        self.assertFalse(self.checker.is_workday(date(2016, 12, 17)))

    @responses.activate
    def test_weekday_is_workday(self):
        self.assertTrue(self.checker.is_workday(date(2016, 12, 21)))

    @responses.activate
    def test_next_workday_middle_of_week(self):
        next_day = self.checker.get_next_workday(date(2016, 12, 21))
        self.assertEqual(next_day, date(2016, 12, 22))

    @responses.activate
    def test_next_workday_weekend(self):
        next_day = self.checker.get_next_workday(date(2016, 12, 16))
        self.assertEqual(next_day, date(2016, 12, 19))

    @responses.activate
    def test_next_workday_bank_holidays(self):
        next_day = self.checker.get_next_workday(date(2016, 12, 23))
        self.assertEqual(next_day, date(2016, 12, 28))

    @responses.activate
    def test_previous_workday_middle_of_week(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 22))
        self.assertEqual(previous_day, date(2016, 12, 21))

    @responses.activate
    def test_previous_workday_weekend(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 19))
        self.assertEqual(previous_day, date(2016, 12, 16))

    @responses.activate
    def test_previous_workday_bank_holidays(self):
        previous_day = self.checker.get_previous_workday(date(2016, 12, 28))
        self.assertEqual(previous_day, date(2016, 12, 23))
