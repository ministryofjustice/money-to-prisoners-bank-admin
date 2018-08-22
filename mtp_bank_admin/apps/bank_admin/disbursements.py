from decimal import Decimal

from django.conf import settings
from mtp_common.api import retrieve_all_pages_for_path

from . import disbursements_config as config, DISBURSEMENTS_LABEL
from .exceptions import EmptyFileError
from .utils import (
    get_start_and_end_date, retrieve_prisons, Journal, get_or_create_file
)

PAYMENT_METHODS = {
    'cheque': 'Cheque',
    'bank_transfer': 'New Bank Details'
}


def get_disbursements_file(api_session, receipt_date, mark_sent=False):
    filepath = get_or_create_file(
        DISBURSEMENTS_LABEL,
        receipt_date,
        generate_disbursements_journal,
        f_args=[api_session, receipt_date],
        file_extension='xlsm'
    )
    if mark_sent:
        mark_as_sent(api_session, receipt_date)
    return open(filepath, 'rb')


class DisbursementJournal(Journal):
    def add_disbursement_row(self, **kwargs):
        for field in self.fields:
            if (kwargs['payment_method'] != PAYMENT_METHODS['bank_transfer'] and
                    field in config.BANK_DETAILS_FIELDS):
                continue
            static_value = self.lookup(field, context=kwargs)
            self.set_field(field, static_value)
        self.next_row()


def retrieve_all_disbursements(api_session, **kwargs):
    return retrieve_all_pages_for_path(
        api_session, 'disbursements/', **kwargs)


def mark_as_sent(api_session, date):
    start_date, end_date = get_start_and_end_date(date)
    disbursements = retrieve_all_disbursements(
        api_session,
        resolution=['confirmed', 'sent'],
        log__action='confirmed',
        logged_at__gte=start_date,
        logged_at__lt=end_date
    )
    if len(disbursements) != 0:
        api_session.post(
            'disbursements/actions/send/',
            json={'disbursement_ids': [d['id'] for d in disbursements]}
        )


def generate_disbursements_journal(api_session, date):
    start_date, end_date = get_start_and_end_date(date)
    disbursements = retrieve_all_disbursements(
        api_session,
        resolution=['confirmed', 'sent'],
        log__action='confirmed',
        logged_at__gte=start_date,
        logged_at__lt=end_date
    )

    if len(disbursements) == 0:
        raise EmptyFileError()

    journal = DisbursementJournal(
        settings.DISBURSEMENT_TEMPLATE_FILEPATH,
        config.DISBURSEMENTS_JOURNAL_SHEET,
        config.DISBURSEMENTS_JOURNAL_START_ROW,
        config.DISBURSEMENT_FIELDS
    )
    prisons = retrieve_prisons(api_session)
    for disbursement in disbursements:
        for field in disbursement:
            if disbursement[field] is None:
                disbursement[field] = ''

        creator = 'Unknown'
        confirmer = 'Unknown'
        for log in disbursement['log_set']:
            if log['action'] == 'created':
                creator = '%s %s' % (
                    log['user']['first_name'][0], log['user']['last_name']
                )
            if log['action'] == 'confirmed':
                confirmer = '%s %s' % (
                    log['user']['first_name'][0], log['user']['last_name']
                )

        journal.add_disbursement_row(
            creator=creator,
            confirmer=confirmer,
            amount_pounds=Decimal(disbursement['amount'])/100,
            prison_ledger_code=prisons[disbursement['prison']]['general_ledger_code'],
            payment_method=PAYMENT_METHODS[disbursement['method']],
            date=date.strftime('%d/%m/%Y'),
            description=disbursement.get('remittance_description') or '',
            **disbursement
        )

    return journal.create_file()
