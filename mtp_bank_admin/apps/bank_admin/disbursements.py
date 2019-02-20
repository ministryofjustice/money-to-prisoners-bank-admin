from decimal import Decimal
import logging

from django.conf import settings
from django.utils.dateparse import parse_date
from mtp_common.api import retrieve_all_pages_for_path

from . import disbursements_config as config, DISBURSEMENTS_LABEL
from .exceptions import EmptyFileError
from .utils import (
    get_start_and_end_date, retrieve_prisons, Journal, get_or_create_file,
    reconcile_for_date,
)

logger = logging.getLogger('mtp')

PAYMENT_METHODS = {
    'cheque': 'Cheque',
    'bank_transfer': 'New Bank Details',
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


def retrieve_private_estate_batches(api_session, start_date, end_date):
    return retrieve_all_pages_for_path(
        api_session,
        'private-estate-batches/',
        date__gte=start_date.date(),
        date__lt=end_date.date(),
    )


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
    start_date, end_date = reconcile_for_date(api_session, date)

    private_estate_batches = retrieve_private_estate_batches(api_session, start_date, end_date)

    disbursements = retrieve_all_disbursements(
        api_session,
        resolution=['confirmed', 'sent'],
        log__action='confirmed',
        logged_at__gte=start_date,
        logged_at__lt=end_date
    )

    if len(private_estate_batches) == 0 and len(disbursements) == 0:
        raise EmptyFileError()

    journal = DisbursementJournal(
        settings.DISBURSEMENT_TEMPLATE_FILEPATH,
        config.DISBURSEMENTS_JOURNAL_SHEET,
        config.DISBURSEMENTS_JOURNAL_START_ROW,
        config.DISBURSEMENT_FIELDS
    )
    journal_date = date.strftime('%d/%m/%Y')
    prisons = retrieve_prisons(api_session)

    add_private_estate_batches(journal, journal_date, prisons, private_estate_batches)
    add_disbursements(journal, journal_date, prisons, disbursements)

    return journal.create_file()


def add_private_estate_batches(journal, journal_date, prisons, private_estate_batches):
    for private_estate_batch in private_estate_batches:
        if not private_estate_batch.get('bank_account'):
            logger.error('Private estate batch missing bank account %(prison)s %(date)s' % private_estate_batch)
            continue
        if not private_estate_batch['total_amount']:
            logger.info('Nothing to transfer to %(prison)s for %(date)s' % private_estate_batch)
            continue
        prison = prisons[private_estate_batch['prison']]
        prison_name = prison.get('short_name') or prison['name']
        bank_account = private_estate_batch['bank_account']
        journal.add_disbursement_row(
            creator='Prisoner money team',
            confirmer='Prisoner money team',
            amount_pounds=Decimal(private_estate_batch['total_amount']) / 100,
            prison_ledger_code=prison['general_ledger_code'],
            payment_method=PAYMENT_METHODS['bank_transfer'],
            date=journal_date,

            invoice_number='PM%s%s' % (prison['nomis_id'], parse_date(private_estate_batch['date']).strftime('%Y%m%d')),
            description='Transfer to %s' % prison_name,

            recipient_first_name='',
            recipient_last_name=prison['name'],
            address_line1=bank_account['address_line1'],
            address_line2=bank_account.get('address_line2') or '',
            city=bank_account['city'],
            postcode=bank_account['postcode'],
            account_number=bank_account['account_number'],
            sort_code=bank_account['sort_code'],
            recipient_email=bank_account['remittance_email'],
        )


def add_disbursements(journal, journal_date, prisons, disbursements):
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
            amount_pounds=Decimal(disbursement['amount']) / 100,
            prison_ledger_code=prisons[disbursement['prison']]['general_ledger_code'],
            payment_method=PAYMENT_METHODS[disbursement['method']],
            date=journal_date,
            description=disbursement.get('remittance_description') or '',
            **disbursement
        )
