from datetime import date, datetime, timezone
from unittest import mock

from mtp_common.auth.api_client import get_api_session
from mtp_common.auth.test_utils import generate_tokens
import requests
import responses

from bank_admin.utils import (
    RECONCILE_MAX_ATTEMPTS, RECONCILE_RETRY_DELAY, WorkdayChecker, reconcile_for_date,
)
from .utils import mock_bank_holidays, api_url, BankAdminTestCase


class ReconcileForDateTestCase(BankAdminTestCase):

    def setUp(self):
        self.api_session = get_api_session(mock.MagicMock(
            user=mock.MagicMock(
                token=generate_tokens()
            )
        ))

    @responses.activate
    def test_reconciles_midweek(self):
        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )

        start_date, end_date = reconcile_for_date(self.api_session, date(2016, 9, 15))

        self.assert_called_with(
            api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 9, 15, 0, 0, tzinfo=timezone.utc).isoformat(),
                'received_at__lt': datetime(2016, 9, 16, 0, 0, tzinfo=timezone.utc).isoformat()
            }
        )

        self.assertEqual(start_date, datetime(2016, 9, 15, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(end_date, datetime(2016, 9, 16, 0, 0, tzinfo=timezone.utc))

    @responses.activate
    def test_reconciles_weekend(self):
        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )

        start_date, end_date = reconcile_for_date(self.api_session, date(2016, 10, 7))

        self.assert_called_with(
            api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 10, 7, 0, 0, tzinfo=timezone.utc).isoformat(),
                'received_at__lt': datetime(2016, 10, 8, 0, 0, tzinfo=timezone.utc).isoformat()
            }
        )
        self.assert_called_with(
            api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 10, 8, 0, 0, tzinfo=timezone.utc).isoformat(),
                'received_at__lt': datetime(2016, 10, 9, 0, 0, tzinfo=timezone.utc).isoformat()
            }
        )
        self.assert_called_with(
            api_url('/transactions/reconcile/'), responses.POST,
            {
                'received_at__gte': datetime(2016, 10, 9, 0, 0, tzinfo=timezone.utc).isoformat(),
                'received_at__lt': datetime(2016, 10, 10, 0, 0, tzinfo=timezone.utc).isoformat()
            }
        )

        self.assertEqual(start_date, datetime(2016, 10, 7, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(end_date, datetime(2016, 10, 10, 0, 0, tzinfo=timezone.utc))

    @responses.activate
    @mock.patch('bank_admin.utils.systime.sleep')
    def test_retries_reconcile_on_timeout(self, mocked_sleep):
        mock_bank_holidays()
        # first attempt times out, second succeeds
        responses.add(
            responses.POST, api_url('/transactions/reconcile/'),
            body=requests.exceptions.ReadTimeout()
        )
        responses.add(responses.POST, api_url('/transactions/reconcile/'), status=200)

        start_date, end_date = reconcile_for_date(self.api_session, date(2016, 9, 15))

        reconcile_calls = [c for c in responses.calls if 'transactions/reconcile/' in c.request.url]
        self.assertEqual(len(reconcile_calls), 2)
        mocked_sleep.assert_called_once_with(RECONCILE_RETRY_DELAY)
        self.assertEqual(start_date, datetime(2016, 9, 15, 0, 0, tzinfo=timezone.utc))
        self.assertEqual(end_date, datetime(2016, 9, 16, 0, 0, tzinfo=timezone.utc))

    @responses.activate
    @mock.patch('bank_admin.utils.systime.sleep')
    def test_reconcile_gives_up_after_max_attempts(self, mocked_sleep):
        mock_bank_holidays()
        for _ in range(RECONCILE_MAX_ATTEMPTS):
            responses.add(
                responses.POST, api_url('/transactions/reconcile/'),
                body=requests.exceptions.ReadTimeout()
            )

        with self.assertRaises(requests.exceptions.Timeout):
            reconcile_for_date(self.api_session, date(2016, 9, 15))

        reconcile_calls = [c for c in responses.calls if 'transactions/reconcile/' in c.request.url]
        self.assertEqual(len(reconcile_calls), RECONCILE_MAX_ATTEMPTS)
        self.assertEqual(mocked_sleep.call_count, RECONCILE_MAX_ATTEMPTS - 1)


class WorkdayCheckerTestCase(BankAdminTestCase):
    @classmethod
    def make_checker(cls, rsps):
        mock_bank_holidays(rsps)
        return WorkdayChecker()

    def test_christmas_is_not_workday(self):
        with responses.RequestsMock() as rsps:
            self.assertFalse(self.make_checker(rsps).is_workday(date(2016, 12, 27)))

    def test_weekend_is_not_workday(self):
        with responses.RequestsMock() as rsps:
            self.assertFalse(self.make_checker(rsps).is_workday(date(2016, 12, 17)))

    def test_weekday_is_workday(self):
        with responses.RequestsMock() as rsps:
            self.assertTrue(self.make_checker(rsps).is_workday(date(2016, 12, 21)))

    def test_next_workday_middle_of_week(self):
        with responses.RequestsMock() as rsps:
            next_day = self.make_checker(rsps).get_next_workday(date(2016, 12, 21))
        self.assertEqual(next_day, date(2016, 12, 22))

    def test_next_workday_weekend(self):
        with responses.RequestsMock() as rsps:
            next_day = self.make_checker(rsps).get_next_workday(date(2016, 12, 16))
        self.assertEqual(next_day, date(2016, 12, 19))

    def test_next_workday_bank_holidays(self):
        with responses.RequestsMock() as rsps:
            next_day = self.make_checker(rsps).get_next_workday(date(2016, 12, 23))
        self.assertEqual(next_day, date(2016, 12, 28))

    def test_previous_workday_middle_of_week(self):
        with responses.RequestsMock() as rsps:
            previous_day = self.make_checker(rsps).get_previous_workday(date(2016, 12, 22))
        self.assertEqual(previous_day, date(2016, 12, 21))

    def test_previous_workday_weekend(self):
        with responses.RequestsMock() as rsps:
            previous_day = self.make_checker(rsps).get_previous_workday(date(2016, 12, 19))
        self.assertEqual(previous_day, date(2016, 12, 16))

    def test_previous_workday_bank_holidays(self):
        with responses.RequestsMock() as rsps:
            previous_day = self.make_checker(rsps).get_previous_workday(date(2016, 12, 28))
        self.assertEqual(previous_day, date(2016, 12, 23))
