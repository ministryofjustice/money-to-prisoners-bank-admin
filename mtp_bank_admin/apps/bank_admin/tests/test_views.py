import datetime
import logging
from unittest import mock

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import SimpleTestCase
from django.utils.encoding import escape_uri_path
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from mtp_common.auth.exceptions import Unauthorized, Forbidden
from mtp_common.auth.test_utils import generate_tokens

from . import (
    get_test_transactions, get_test_credits, NO_TRANSACTIONS, TEST_PRISONS_RESPONSE
)
from .test_refund import REFUND_TRANSACTIONS, expected_output
from ..types import PaymentType


class BankAdminViewTestCase(SimpleTestCase):

    def setUp(self):
        logging.disable(logging.CRITICAL)

    @mock.patch('mtp_common.auth.backends.api_client')
    def login(self, mock_api_client):
        mock_api_client.authenticate.return_value = {
            'pk': 5,
            'token': generate_tokens(),
            'user_data': {
                'first_name': 'Sam',
                'last_name': 'Hall',
                'username': 'shall',
                'applications': ['bank-admin'],
                'permissions': ['transaction.view_bank_details_transaction']
            }
        }

        response = self.client.post(
            reverse('login'),
            data={'username': 'shall', 'password': 'pass'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)

    def check_login_redirect(self, attempted_url):
        response = self.client.get(attempted_url)
        redirect_url = '%(login_url)s?next=%(attempted_url)s' % \
            {'login_url': reverse('login'),
             'attempted_url': escape_uri_path(attempted_url)}
        self.assertRedirects(response, redirect_url)


class DashboardButtonVisibilityTestCase(BankAdminViewTestCase):
    @mock.patch('mtp_common.auth.backends.api_client')
    def test_cannot_login_without_app_access(self, mock_api_client):
        mock_api_client.authenticate.side_effect = Forbidden

        response = self.client.post(
            reverse('login'),
            data={'username': 'shall', 'password': 'pass'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['form'].is_valid())

    @mock.patch('mtp_common.auth.backends.api_client')
    def test_can_see_refund_download_with_perm(self, mock_api_client):
        mock_api_client.authenticate.return_value = {
            'pk': 5,
            'token': generate_tokens(),
            'user_data': {
                'first_name': 'Sam',
                'last_name': 'Hall',
                'username': 'shall',
                'applications': ['bank-admin'],
                'permissions': ['transaction.view_bank_details_transaction']
            }
        }

        response = self.client.post(
            reverse('login'),
            data={'username': 'shall', 'password': 'pass'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse('bank_admin:download_refund_file'))

    @mock.patch('mtp_common.auth.backends.api_client')
    def test_cannot_see_refund_download_without_perm(self, mock_api_client):
        mock_api_client.authenticate.return_value = {
            'pk': 5,
            'token': generate_tokens(),
            'user_data': {
                'first_name': 'Sam',
                'last_name': 'Hall',
                'username': 'shall',
                'applications': ['bank-admin'],
                'permissions': []
            }
        }

        response = self.client.post(
            reverse('login'),
            data={'username': 'shall', 'password': 'pass'},
            follow=True
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, reverse('bank_admin:download_refund_file'))


class DownloadRefundFileViewTestCase(BankAdminViewTestCase):

    def test_dashboard_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:dashboard'))

    def test_download_refund_file_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_refund_file'))

    @mock.patch('bank_admin.refund.api_client')
    @mock.patch('bank_admin.utils.api_client')
    def test_download_refund_file(self, mock_api_client, mock_refund_api_client):
        self.login()

        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = REFUND_TRANSACTIONS

        response = self.client.get(reverse('bank_admin:download_refund_file') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            bytes(expected_output(), 'utf8'),
            response.content
        )

    @mock.patch('bank_admin.refund.api_client')
    @mock.patch('bank_admin.utils.api_client')
    def test_accesspay_queries_by_date(self, mock_api_client, mock_refund_api_client):
        self.login()

        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = {
            'count': 1,
            'results': [{
                'id': '3',
                'amount': 2568,
                'sender_account_number': '22222222',
                'sender_sort_code': '111111',
                'sender_name': 'John Doe',
                'ref_code': '900001',
                'reference': 'for birthday',
                'credited': False,
                'refunded': False,
                'received_at': '2014-11-12'
            }]
        },

        self.client.get(
            reverse('bank_admin:download_refund_file') +
            '?receipt_date=2014-11-12'
        )

        conn.get.assert_called_with(
            limit=settings.REQUEST_PAGE_SIZE,
            offset=0,
            status='refundable',
            received_at__gte=datetime.datetime(2014, 11, 11, 23, 0, tzinfo=utc),
            received_at__lt=datetime.datetime(2014, 11, 12, 23, 0, tzinfo=utc)
        )


@mock.patch('bank_admin.utils.api_client')
class DownloadRefundFileErrorViewTestCase(BankAdminViewTestCase):

    @mock.patch('mtp_common.auth.backends.api_client')
    def test_download_refund_file_unauthorized(self, auth_api_client, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = Unauthorized()

        response = self.client.get(reverse('bank_admin:download_refund_file') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    def test_download_refund_file_no_transactions_error_message(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection()
        conn.transactions.get.return_value = NO_TRANSACTIONS

        response = self.client.get(
            reverse('bank_admin:download_refund_file') + '?receipt_date=2014-12-11',
            follow=True
        )

        self.assertContains(response, _('No transactions available'),
                            status_code=200)


class DownloadAdiFileViewTestCase(BankAdminViewTestCase):

    def _set_returned_transactions(self, mock_api_client):
        credits = get_test_credits(20)
        refundable_transactions = get_test_transactions(PaymentType.refund, 5)
        rejected_transactions = get_test_transactions(PaymentType.reject, 2)

        conn = mock_api_client.get_connection()
        conn.prisons.get.return_value = TEST_PRISONS_RESPONSE
        conn.credits.get.return_value = credits
        conn.transactions.get.side_effect = [
            refundable_transactions,
            rejected_transactions
        ]

        return conn

    def test_dashboard_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:dashboard'))

    def test_download_adi_journal_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_adi_journal') +
                                  '?receipt_date=2014-12-11')

    @mock.patch('bank_admin.utils.api_client')
    def test_download_adi_journal(self, mock_api_client):
        self.login()

        self._set_returned_transactions(mock_api_client)

        response = self.client.get(reverse('bank_admin:download_adi_journal') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', response['Content-Type'])

    @mock.patch('bank_admin.utils.api_client')
    def test_adi_journal_queries_by_date(self, mock_api_client):
        self.login()

        conn = self._set_returned_transactions(mock_api_client)

        self.client.get(
            reverse('bank_admin:download_adi_journal') +
            '?receipt_date=2014-11-12'
        )

        conn.credits.get.assert_called_with(
            limit=settings.REQUEST_PAGE_SIZE,
            offset=0,
            valid=True,
            received_at__gte=datetime.datetime(2014, 11, 11, 23, 0, tzinfo=utc),
            received_at__lt=datetime.datetime(2014, 11, 12, 23, 0, tzinfo=utc)
        )
        conn.transactions.get.assert_has_calls([
            mock.call(
                limit=settings.REQUEST_PAGE_SIZE,
                offset=0,
                status='refundable',
                received_at__gte=datetime.datetime(2014, 11, 11, 23, 0, tzinfo=utc),
                received_at__lt=datetime.datetime(2014, 11, 12, 23, 0, tzinfo=utc)
            ),
            mock.call(
                limit=settings.REQUEST_PAGE_SIZE,
                offset=0,
                status='unidentified',
                received_at__gte=datetime.datetime(2014, 11, 11, 23, 0, tzinfo=utc),
                received_at__lt=datetime.datetime(2014, 11, 12, 23, 0, tzinfo=utc)
            )
        ])


@mock.patch('bank_admin.utils.api_client')
class DownloadAdiFileErrorViewTestCase(BankAdminViewTestCase):

    @mock.patch('mtp_common.auth.backends.api_client')
    def test_download_adi_journal_unauthorized(self, auth_api_client, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().credits
        conn.get.side_effect = Unauthorized()

        response = self.client.get(reverse('bank_admin:download_adi_journal') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    def test_download_adi_journal_no_transactions_error_message(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection()
        conn.prisons.get.return_value = TEST_PRISONS_RESPONSE
        conn.credits.get.return_value = NO_TRANSACTIONS
        conn.transactions.get.return_value = NO_TRANSACTIONS

        response = self.client.get(reverse('bank_admin:download_adi_journal') +
                                   '?receipt_date=2014-12-11',
                                   follow=True)

        self.assertContains(response, _('No transactions available'),
                            status_code=200)

    def test_download_adi_journal_invalid_receipt_date(self, mock_api_client):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_adi_journal') + '?receipt_date=bleh',
            follow=True
        )

        self.assertContains(response,
                            _("Invalid format for receipt_date"),
                            status_code=400)

    def test_download_adi_journal_missing_receipt_date(self, mock_api_client):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_adi_journal'),
            follow=True
        )

        self.assertContains(response,
                            _("'receipt_date' parameter required"),
                            status_code=400)


class DownloadBankStatementViewTestCase(BankAdminViewTestCase):

    def test_download_bank_statement_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_bank_statement') +
                                  '?receipt_date=2014-12-11')

    @mock.patch('bank_admin.utils.api_client')
    def test_download_bank_statement(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = get_test_transactions()

        response = self.client.get(reverse('bank_admin:download_bank_statement') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/octet-stream', response['Content-Type'])

    @mock.patch('bank_admin.utils.api_client')
    def test_bank_statement_queries_by_date(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().transactions
        conn.get.return_value = get_test_transactions()

        self.client.get(
            reverse('bank_admin:download_bank_statement') +
            '?receipt_date=2014-11-12'
        )

        conn.get.assert_called_with(
            limit=settings.REQUEST_PAGE_SIZE,
            offset=0,
            received_at__gte=datetime.datetime(2014, 11, 11, 23, 0, tzinfo=utc),
            received_at__lt=datetime.datetime(2014, 11, 12, 23, 0, tzinfo=utc)
        )


@mock.patch('bank_admin.utils.api_client')
class DownloadBankStatementErrorViewTestCase(BankAdminViewTestCase):

    @mock.patch('mtp_common.auth.backends.api_client')
    def test_unauthorized(self, auth_api_client, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().transactions
        conn.get.side_effect = Unauthorized()

        response = self.client.get(reverse('bank_admin:download_bank_statement') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    def test_invalid_receipt_date_returns_error(self, mock_api_client):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_bank_statement') + '?receipt_date=bleh',
            follow=True
        )

        self.assertContains(response,
                            _("Invalid format for receipt_date"),
                            status_code=400)

    def test_missing_receipt_date_returns_error(self, mock_api_client):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_bank_statement'),
            follow=True
        )

        self.assertContains(response,
                            _("'receipt_date' parameter required"),
                            status_code=400)
