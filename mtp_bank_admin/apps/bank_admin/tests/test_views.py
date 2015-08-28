from unittest import mock
from django.test import SimpleTestCase
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from moj_auth.tests.utils import generate_tokens

from .test_refund import REFUND_TRANSACTION


class BankAdminViewsTestCase(SimpleTestCase):

    @mock.patch('moj_auth.backends.api_client')
    def login(self, mock_api_client):
        mock_api_client.authenticate.return_value = {
            'pk': 5,
            'token': generate_tokens(),
            'user_data': {
                'first_name': 'Sam',
                'last_name': 'Hall',
                'username': 'shall'
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
             'attempted_url': attempted_url}
        self.assertRedirects(response, redirect_url)

    def test_requires_login_dashboard(self):
        self.check_login_redirect(reverse('bank_admin:dashboard'))

    def test_requires_download_refund_file(self):
        self.check_login_redirect(reverse('bank_admin:download_refund_file'))

    @mock.patch('bank_admin.refund.api_client')
    def test_download_refund_file(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = REFUND_TRANSACTION

        response = self.client.get(reverse('bank_admin:download_refund_file'))

        self.assertEqual(200, response.status_code)
        self.assertEqual('text/csv', response['Content-Type'])
        self.assertEqual(bytes('111111,22222222,DOE JO,25.68,%s\r\n' % settings.REFUND_REFERENCE, 'utf8'),
                         response.content)

    @mock.patch('bank_admin.refund.api_client')
    def test_download_refund_file_error(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.side_effect = Exception('Problem?')

        response = self.client.get(reverse('bank_admin:download_refund_file'),
                                   follow=True)

        self.assertContains(response, _('Could not download AccessPay file'),
                            status_code=200)

    @mock.patch('bank_admin.refund.api_client')
    def test_download_refund_file_no_transactions(self, mock_api_client):
        self.login()

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = []

        response = self.client.get(reverse('bank_admin:download_refund_file'),
                                   follow=True)

        self.assertContains(response,
                            _('No new transactions available for refund'),
                            status_code=200)
