from decimal import Decimal

from django.conf import settings
from mtp_common.api import retrieve_all_pages_for_path
from mtp_common.auth import api_client

from . import disbursements_config as config
from .exceptions import EmptyFileError
from .utils import get_start_and_end_date, retrieve_prisons, Journal

PAYMENT_METHODS = {
    'cheque': 'Cheque',
    'bank_transfer': 'New Bank Details'
}


class DisbursementJournal(Journal):
    def add_disbursement_row(self, **kwargs):
        for field in self.fields:
            if (kwargs['payment_method'] != PAYMENT_METHODS['bank_transfer'] and
                    field in config.BANK_DETAILS_FIELDS):
                continue
            static_value = self.lookup(field, context=kwargs)
            self.set_field(field, static_value)
        self.next_row()


def retrieve_all_disbursements(request, **kwargs):
    session = api_client.get_api_session(request)
    return retrieve_all_pages_for_path(
        session, 'disbursements/', **kwargs)


def mark_as_sent(request, disbursements):
    session = api_client.get_api_session(request)
    session.post(
        'disbursements/actions/send/',
        json={'disbursement_ids': [d['id'] for d in disbursements]}
    )


def generate_disbursements_journal(request, date):
    start_date, end_date = get_start_and_end_date(date)
    disbursements = retrieve_all_disbursements(
        request,
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
    prisons = retrieve_prisons(request)
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
            description='',
            **disbursement
        )

    mark_as_sent(request, disbursements)

    return (
        settings.DISBURSEMENT_OUTPUT_FILENAME.format(date=date.today()),
        journal.create_file()
    )
