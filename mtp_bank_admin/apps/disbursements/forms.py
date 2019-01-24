import logging

from django import forms
from django.utils.translation import gettext_lazy as _
from form_error_reporting import GARequestErrorReportingMixin
from mtp_common.auth.api_client import get_api_session
from requests.exceptions import RequestException

logger = logging.getLogger('mtp')


class ChooseDisbursementForm(GARequestErrorReportingMixin, forms.Form):
    invoice_number = forms.CharField(label=_('Invoice number of the disbursement you wish to cancel'))

    error_messages = {
        'connection': _('This service is currently unavailable'),
        'not_found': _('That invoice number does not match a disbursement'),
        'not_confirmed': _('That disbursement cannot be cancelled yet'),
        'cancelled': _('That disbursement has already been cancelled'),
    }

    def __init__(self, request=None, **kwargs):
        super().__init__(**kwargs)
        self.request = request

    def clean_invoice_number(self):
        session = get_api_session(self.request)
        try:
            disbursements = session.get(
                '/disbursements/', params={'invoice_number': self.cleaned_data['invoice_number']}
            ).json()
        except RequestException:
            raise forms.ValidationError(
                self.error_messages['connection'], code='connection'
            )

        if disbursements['count'] != 1:
            raise forms.ValidationError(
                self.error_messages['not_found'], code='not_found'
            )

        disbursement = disbursements['results'][0]

        if disbursement['resolution'] == 'cancelled':
            raise forms.ValidationError(
                self.error_messages['cancelled'], code='cancelled'
            )

        if disbursement['resolution'] not in ['sent', 'confirmed']:
            raise forms.ValidationError(
                self.error_messages['not_confirmed'], code='not_confirmed'
            )

        self.disbursement = disbursement
        return self.cleaned_data['invoice_number']


class CancelDisbursementForm(ChooseDisbursementForm):
    reason = forms.ChoiceField(choices=[
        ('Invalid sort code', _('Invalid sort code'),),
        ('Invalid bank account number', _('Invalid bank account number'),),
        ('Invalid address', _('Invalid address'),),
        ('Cheque cancelled', _('Cheque cancelled'),),
        ('DUPLICATE', _('Duplicate invoice reference number'),),
    ])

    def clean_reason(self):
        if self.cleaned_data['reason'] == 'DUPLICATE':
            raise forms.ValidationError(
                'Disbursements rejected for a duplicate invoice reference '
                'number do not need to be and should not be cancelled'
            )
        return self.cleaned_data['reason']

    def cancel_disbursement(self):
        session = get_api_session(self.request)
        session.post(
            '/disbursements/actions/cancel/',
            json={'disbursement_ids': [self.disbursement['id']]}
        )

        comments = [{
            'disbursement': self.disbursement['id'],
            'comment': self.cleaned_data['reason'],
            'category': 'cancel',
        }]
        session.post('/disbursements/comments/', json=comments)
