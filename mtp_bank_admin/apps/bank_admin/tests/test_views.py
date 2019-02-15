from datetime import date, datetime, timedelta
import logging
from unittest import mock
from urllib.parse import quote_plus

from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.encoding import escape_uri_path
from django.utils.timezone import utc
from django.utils.translation import ugettext_lazy as _
from mtp_common.auth.exceptions import Forbidden
from mtp_common.auth.test_utils import generate_tokens
from mtp_common.test_utils import silence_logger
import responses

from .utils import (
    get_test_transactions, get_test_credits, NO_TRANSACTIONS,
    mock_balance, api_url, mock_bank_holidays, mock_list_prisons,
    BankAdminTestCase, get_test_disbursements
)
from .test_refund import REFUND_TRANSACTIONS, expected_output
from .test_statement import mock_test_transactions
from bank_admin import (
    ADI_JOURNAL_LABEL, ACCESSPAY_LABEL, MT940_STMT_LABEL, DISBURSEMENTS_LABEL
)
from bank_admin.types import PaymentType
from bank_admin.utils import set_worldpay_cutoff


def mock_missing_download_check():
    mock_bank_holidays()
    responses.add(
        responses.GET,
        api_url('/file-downloads/missing/'),
        json={'missing_dates': []}
    )


class BankAdminViewTestCase(BankAdminTestCase):
    @mock.patch('mtp_common.auth.backends.api_client')
    def login(self, mock_api_client):
        mock_api_client.authenticate.return_value = {
            'pk': 5,
            'token': generate_tokens(),
            'user_data': {
                'first_name': 'Sam',
                'last_name': 'Hall',
                'username': 'shall',
                'permissions': ['transaction.view_bank_details_transaction']
            }
        }

        response = self.client.post(
            reverse('login'),
            data={'username': 'shall', 'password': 'pass'},
            follow=False
        )

        self.assertEqual(response.status_code, 302)

    def check_login_redirect(self, attempted_url):
        response = self.client.get(attempted_url)
        redirect_url = '%(login_url)s?next=%(attempted_url)s' % \
            {'login_url': reverse('login'),
             'attempted_url': escape_uri_path(attempted_url)}
        self.assertRedirects(response, redirect_url)


class LocaleTestCase(BankAdminViewTestCase):
    def test_locale_switches_based_on_browser_language(self):
        languages = (
            ('*', 'en-gb'),
            ('en', 'en-gb'),
            ('en-gb', 'en-gb'),
            ('en-GB, en, *', 'en-gb'),
            ('cy', 'cy'),
            ('cy, en-GB, en, *', 'cy'),
            ('en, cy, *', 'en-gb'),
            ('es', 'en-gb'),
        )
        with silence_logger(name='django.request', level=logging.ERROR):
            for accept_language, expected_slug in languages:
                response = self.client.get('/', HTTP_ACCEPT_LANGUAGE=accept_language)
                self.assertRedirects(response, '/%s/' % expected_slug, fetch_redirect_response=False)
                response = self.client.get('/login/', HTTP_ACCEPT_LANGUAGE=accept_language)
                self.assertRedirects(response, '/%s/login/' % expected_slug, fetch_redirect_response=True)


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

    @responses.activate
    @mock.patch('mtp_common.auth.backends.api_client')
    def test_can_see_refund_download_with_perm(self, mock_api_client):
        mock_api_client.authenticate.return_value = {
            'pk': 5,
            'token': generate_tokens(),
            'user_data': {
                'first_name': 'Sam',
                'last_name': 'Hall',
                'username': 'shall',
                'permissions': ['transaction.view_bank_details_transaction']
            }
        }
        mock_missing_download_check()

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

    def _set_returned_refunds(self):
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            json=REFUND_TRANSACTIONS
        )
        responses.add(
            responses.PATCH,
            api_url('/transactions/'),
            status=200
        )
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )
        mock_bank_holidays()

        return REFUND_TRANSACTIONS

    def test_dashboard_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:dashboard'))

    def test_download_refund_file_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_refund_file'))

    @responses.activate
    def test_download_refund_file(self):
        self.login()

        self._set_returned_refunds()

        response = self.client.get(reverse('bank_admin:download_refund_file') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('text/plain', response['Content-Type'])
        self.assertEqual(
            expected_output().encode('utf8'),
            response.content
        )

    @responses.activate
    def test_accesspay_queries_by_date(self):
        self.login()

        self._set_returned_refunds()

        self.client.get(
            reverse('bank_admin:download_refund_file') +
            '?receipt_date=2014-11-12'
        )

        self.assert_called_with(
            api_url('/transactions/'), responses.GET,
            dict(
                limit=str(settings.REQUEST_PAGE_SIZE),
                offset='0',
                status='refundable',
                received_at__gte=str(datetime(2014, 11, 12, 0, 0, tzinfo=utc)),
                received_at__lt=str(datetime(2014, 11, 13, 0, 0, tzinfo=utc))
            )
        )
        self.assert_called_with(
            api_url('/file-downloads/'), responses.POST,
            dict(
                label=ACCESSPAY_LABEL,
                date='2014-11-12'
            )
        )

    @responses.activate
    def test_disbursements_marked_as_sent(self):
        self.login()

        refunds = self._set_returned_refunds()

        self.client.get(reverse('bank_admin:download_refund_file') +
                        '?receipt_date=2014-12-11')

        self.assert_called_with(
            api_url('transactions/'), responses.PATCH,
            [{'id': r['id'], 'refunded': True} for r in refunds['results']]
        )


class DownloadRefundFileErrorViewTestCase(BankAdminViewTestCase):

    @responses.activate
    def test_download_refund_file_unauthorized(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            status=401
        )
        responses.add(
            responses.POST,
            api_url('/oauth2/revoke_token/'),
            status=200
        )

        response = self.client.get(reverse('bank_admin:download_refund_file') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    @responses.activate
    def test_download_refund_file_no_transactions_error_message(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            json=NO_TRANSACTIONS
        )
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )
        mock_missing_download_check()

        response = self.client.get(
            reverse('bank_admin:download_refund_file') + '?receipt_date=2014-12-11',
            follow=True
        )

        self.assertContains(response, _('No transactions available'),
                            status_code=200)


class DownloadAdiFileViewTestCase(BankAdminViewTestCase):

    def _set_returned_transactions(self):
        credits = get_test_credits(20)
        refundable_transactions = get_test_transactions(PaymentType.refund, 5)
        rejected_transactions = get_test_transactions(PaymentType.reject, 2)

        receipt_date = date(2014, 12, 11)
        start_date = quote_plus(str(set_worldpay_cutoff(receipt_date)))
        end_date = quote_plus(str(set_worldpay_cutoff(receipt_date + timedelta(days=1))))

        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        mock_list_prisons()
        responses.add(
            responses.GET,
            api_url('/credits/'),
            json=credits
        )
        responses.add(
            responses.GET,
            api_url(
                '/transactions/?offset=0&limit=500'
                '&received_at__lt={end_date}'
                '&received_at__gte={start_date}'
                '&status=refundable'.format(
                    start_date=start_date, end_date=end_date
                )
            ),
            json=refundable_transactions,
            match_querystring=True
        )
        responses.add(
            responses.GET,
            api_url(
                '/transactions/?offset=0&limit=500'
                '&received_at__lt={end_date}'
                '&received_at__gte={start_date}'
                '&status=unidentified'.format(
                    start_date=start_date, end_date=end_date
                )
            ),
            json=rejected_transactions,
            match_querystring=True
        )
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )
        mock_bank_holidays()

    def test_dashboard_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:dashboard'))

    def test_download_adi_journal_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_adi_journal') +
                                  '?receipt_date=2014-12-11')

    @responses.activate
    def test_download_adi_journal(self):
        self.login()

        self._set_returned_transactions()

        response = self.client.get(reverse('bank_admin:download_adi_journal') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', response['Content-Type'])

    @responses.activate
    def test_adi_journal_queries_by_date(self):
        self.login()

        self._set_returned_transactions()

        self.client.get(
            reverse('bank_admin:download_adi_journal') +
            '?receipt_date=2014-12-11'
        )

        start_date = str(datetime(2014, 12, 11, 0, 0, tzinfo=utc))
        end_date = str(datetime(2014, 12, 12, 0, 0, tzinfo=utc))

        self.assert_called_with(
            api_url('/credits/'), responses.GET,
            dict(
                limit=str(settings.REQUEST_PAGE_SIZE),
                offset='0',
                valid='True',
                received_at__gte=start_date,
                received_at__lt=end_date
            )
        )

        self.assert_called_with(
            api_url('/transactions/'), responses.GET,
            dict(
                limit=str(settings.REQUEST_PAGE_SIZE),
                offset='0',
                status='refundable',
                received_at__gte=start_date,
                received_at__lt=end_date
            )
        )

        self.assert_called_with(
            api_url('/transactions/'), responses.GET,
            dict(
                limit=str(settings.REQUEST_PAGE_SIZE),
                offset='0',
                status='unidentified',
                received_at__gte=start_date,
                received_at__lt=end_date
            )
        )

        self.assert_called_with(
            api_url('/file-downloads/'), responses.POST,
            dict(
                label=ADI_JOURNAL_LABEL,
                date='2014-12-11'
            )
        )


class DownloadAdiFileErrorViewTestCase(BankAdminViewTestCase):

    @responses.activate
    def test_download_adi_journal_unauthorized(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/credits/'),
            status=401
        )
        responses.add(
            responses.POST,
            api_url('/oauth2/revoke_token/'),
            status=200
        )

        response = self.client.get(reverse('bank_admin:download_adi_journal') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    @responses.activate
    def test_download_adi_journal_no_transactions_error_message(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        mock_list_prisons()
        responses.add(
            responses.GET,
            api_url('/credits/'),
            json=NO_TRANSACTIONS
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            json=NO_TRANSACTIONS
        )
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )
        mock_missing_download_check()

        response = self.client.get(reverse('bank_admin:download_adi_journal') +
                                   '?receipt_date=2014-12-11',
                                   follow=True)

        self.assertContains(response, _('No transactions available'),
                            status_code=200)

    def test_download_adi_journal_invalid_receipt_date(self):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_adi_journal') + '?receipt_date=bleh',
            follow=True
        )

        self.assertContains(response,
                            _("Invalid format for receipt_date"),
                            status_code=400)

    def test_download_adi_journal_missing_receipt_date(self):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_adi_journal'),
            follow=True
        )

        self.assertContains(response,
                            _("'receipt_date' parameter required"),
                            status_code=400)


class DownloadBankStatementViewTestCase(BankAdminViewTestCase):

    def _generate_bank_statement(self):
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        mock_test_transactions()
        mock_balance()
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )
        mock_bank_holidays()

    def test_download_bank_statement_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_bank_statement') +
                                  '?receipt_date=2014-12-11')

    @responses.activate
    def test_download_bank_statement(self):
        self.login()

        self._generate_bank_statement()

        response = self.client.get(reverse('bank_admin:download_bank_statement') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/octet-stream', response['Content-Type'])

    @responses.activate
    def test_bank_statement_queries_by_date(self):
        self.login()

        self._generate_bank_statement()

        self.client.get(
            reverse('bank_admin:download_bank_statement') +
            '?receipt_date=2014-11-12'
        )

        self.assert_called_with(
            api_url('/transactions/'), responses.GET,
            dict(
                limit=str(settings.REQUEST_PAGE_SIZE),
                offset='0',
                received_at__gte=str(datetime(2014, 11, 12, 0, 0, tzinfo=utc)),
                received_at__lt=str(datetime(2014, 11, 13, 0, 0, tzinfo=utc))
            )
        )
        self.assert_called_with(
            api_url('/file-downloads/'), responses.POST,
            dict(
                label=MT940_STMT_LABEL,
                date='2014-11-12'
            )
        )


class DownloadBankStatementErrorViewTestCase(BankAdminViewTestCase):

    @responses.activate
    def test_unauthorized(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/transactions/'),
            status=401
        )
        responses.add(
            responses.POST,
            api_url('/oauth2/revoke_token/'),
            status=200
        )

        response = self.client.get(reverse('bank_admin:download_bank_statement') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    def test_invalid_receipt_date_returns_error(self):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_bank_statement') + '?receipt_date=bleh',
            follow=True
        )

        self.assertContains(response,
                            _("Invalid format for receipt_date"),
                            status_code=400)

    def test_missing_receipt_date_returns_error(self):
        self.login()

        response = self.client.get(
            reverse('bank_admin:download_bank_statement'),
            follow=True
        )

        self.assertContains(response,
                            _("'receipt_date' parameter required"),
                            status_code=400)


class DownloadDisbursementsFileViewTestCase(BankAdminViewTestCase):

    def _set_returned_disbursements(self):
        disbursements = get_test_disbursements(20)

        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        mock_bank_holidays()
        mock_list_prisons()
        responses.add(
            responses.GET,
            api_url('/private-estate-batches/'),
            json=NO_TRANSACTIONS
        )
        responses.add(
            responses.GET,
            api_url('/disbursements/'),
            json=disbursements
        )
        responses.add(
            responses.POST,
            api_url('/disbursements/actions/send/'),
            status=200
        )
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )

        return disbursements

    def test_download_disbursements_requires_login(self):
        self.check_login_redirect(reverse('bank_admin:download_disbursements') +
                                  '?receipt_date=2014-12-11')

    @responses.activate
    def test_download_disbursements(self):
        self.login()

        self._set_returned_disbursements()

        response = self.client.get(reverse('bank_admin:download_disbursements') +
                                   '?receipt_date=2014-12-11')

        self.assertEqual(200, response.status_code)
        self.assertEqual('application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', response['Content-Type'])

    @responses.activate
    def test_disbursements_queries_by_date(self):
        self.login()

        self._set_returned_disbursements()

        self.client.get(
            reverse('bank_admin:download_disbursements') +
            '?receipt_date=2014-12-11'
        )

        start_date = str(datetime(2014, 12, 11, 0, 0, tzinfo=utc))
        end_date = str(datetime(2014, 12, 12, 0, 0, tzinfo=utc))

        self.assert_called_with(
            api_url('/disbursements/'), responses.GET,
            dict(
                limit=str(settings.REQUEST_PAGE_SIZE),
                offset='0',
                resolution=['confirmed', 'sent'],
                log__action='confirmed',
                logged_at__gte=start_date,
                logged_at__lt=end_date
            )
        )
        self.assert_called_with(
            api_url('/file-downloads/'), responses.POST,
            dict(
                label=DISBURSEMENTS_LABEL,
                date='2014-12-11'
            )
        )

    @responses.activate
    def test_disbursements_marked_as_sent(self):
        self.login()

        disbursements = self._set_returned_disbursements()

        self.client.get(reverse('bank_admin:download_disbursements') +
                        '?receipt_date=2014-12-11')

        self.assert_called_with(
            api_url('disbursements/actions/send/'), responses.POST,
            {'disbursement_ids': [d['id'] for d in disbursements['results']]}
        )


class DownloadDisbursementsFileErrorViewTestCase(BankAdminViewTestCase):

    @responses.activate
    def test_download_disbursements_unauthorized(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=401
        )
        responses.add(
            responses.GET,
            api_url('/private-estate-batches/'),
            status=401
        )
        responses.add(
            responses.GET,
            api_url('/disbursements/'),
            status=401
        )
        responses.add(
            responses.POST,
            api_url('/oauth2/revoke_token/'),
            status=200
        )

        response = self.client.get(reverse('bank_admin:download_disbursements') +
                                   '?receipt_date=2014-12-11',
                                   follow=False)

        self.assertRedirects(response, reverse('login'))

    @responses.activate
    def test_download_disbursements_no_transactions_error_message(self):
        self.login()

        mock_bank_holidays()
        responses.add(
            responses.POST,
            api_url('/transactions/reconcile/'),
            status=200
        )
        responses.add(
            responses.GET,
            api_url('/private-estate-batches/'),
            json=NO_TRANSACTIONS
        )
        responses.add(
            responses.GET,
            api_url('/disbursements/'),
            json=NO_TRANSACTIONS
        )
        responses.add(
            responses.POST,
            api_url('/file-downloads/'),
            status=200
        )
        mock_list_prisons()
        mock_missing_download_check()

        response = self.client.get(reverse('bank_admin:download_disbursements') +
                                   '?receipt_date=2014-12-11',
                                   follow=True)

        self.assertContains(response, _('No transactions available'),
                            status_code=200)

    def test_download_disbursements_invalid_receipt_date(self):
        self.login()

        mock_bank_holidays()
        response = self.client.get(
            reverse('bank_admin:download_disbursements') + '?receipt_date=bleh',
            follow=True
        )

        self.assertContains(response,
                            _("Invalid format for receipt_date"),
                            status_code=400)

    def test_download_disbursements_missing_receipt_date(self):
        self.login()

        mock_bank_holidays()
        response = self.client.get(
            reverse('bank_admin:download_disbursements'),
            follow=True
        )

        self.assertContains(response,
                            _("'receipt_date' parameter required"),
                            status_code=400)
