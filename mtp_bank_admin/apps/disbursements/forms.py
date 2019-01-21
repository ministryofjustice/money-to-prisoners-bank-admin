import logging

from django import forms
from django.utils.translation import gettext_lazy as _
from form_error_reporting import GARequestErrorReportingMixin
from mtp_common.auth.api_client import get_api_session
from mtp_common import nomis
from requests.exceptions import HTTPError, RequestException

logger = logging.getLogger('mtp')


class ChooseDisbursementForm(GARequestErrorReportingMixin, forms.Form):
    invoice_number = forms.CharField()

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
        nomis_id = self.refund_disbursement(self.disbursement)

        session.post(
            '/disbursements/actions/cancel/',
            json={'disbursement_ids': [self.disbursement['id']]}
        )

        comments = [{
            'disbursement': self.disbursement['id'],
            'comment': self.cleaned_data['reason'],
            'category': 'cancel',
        }]
        if nomis_id:
            comments.append({
                'disbursement': self.disbursement['id'],
                'comment': 'NOMIS refund ref: {nomis_id}'.format(
                    nomis_id=nomis_id
                ),
                'category': 'cancel',
            })
        session.post('/disbursements/comments/', json=comments)

    def refund_disbursement(self, disbursement):
        try:
            nomis_response = nomis.create_transaction(
                prison_id=disbursement['prison'],
                prisoner_number=disbursement['prisoner_number'],
                amount=disbursement['amount']*-1,
                record_id='refund-d%s' % disbursement['id'],
                description='Refund of cancelled disbursement {invoice_number}'.format(
                    invoice_number=disbursement['invoice_number'],
                ),
                transaction_type='RELA',
                retries=1
            )
            return nomis_response['id']
        except HTTPError as e:
            if e.response.status_code == 409:
                logger.warning(
                    'Disbursement %s has already been refunded in NOMIS' % disbursement['id']
                )
                return None
            elif e.response.status_code >= 500:
                logger.error(
                    'Disbursement %s could not be refunded as NOMIS is unavailable'
                    % disbursement['id']
                )
                self.add_error(None, self.error_messages['connection'])
            else:
                logger.warning('Could not refund disbursement %s' % disbursement['id'])
                self.add_error(None, self.error_messages['connection'])
        except RequestException:
            logger.exception(
                'Disbursement %s could not be refunded as NOMIS is unavailable'
                % disbursement['id']
            )
            self.add_error(None, self.error_messages['connection'])
