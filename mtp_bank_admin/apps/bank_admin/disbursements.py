from django.conf import settings
from mtp_common.api import retrieve_all_pages_for_path
from mtp_common.auth import api_client

from . import disbursements_config as config, Journal
from .utils import get_start_and_end_date


class DisbursementJournal(Journal):
    def add_disbursement_row(self, **kwargs):
        for field in self.fields:
            static_value = self.lookup(field, context=kwargs)
            self.set_field(field, static_value)


def retrieve_all_confirmed_disbursements(request, **kwargs):
    session = api_client.get_api_session(request)
    return retrieve_all_pages_for_path(
        session, 'disbursements/', resolution='confirmed', **kwargs)


def generate_disbursements_journal(request, date):
    start_date, end_date = get_start_and_end_date(date)
    disbursements = retrieve_all_confirmed_disbursements(
        request,
        confirmed_at__gte=start_date,
        confirmed_at__lt=end_date
    )

    journal = DisbursementJournal(
        settings.DISBURSEMENT_TEMPLATE_FILEPATH,
        config.DISBURSEMENTS_JOURNAL_SHEET,
        config.DISBURSEMENTS_JOURNAL_START_ROW,
        config.DISBURSEMENT_FIELDS
    )
    for disbursement in disbursements:
        journal.add_disbursement_row(**disbursement)

    return (
        settings.DISBURSEMENT_OUTPUT_FILENAME.format(date=date.today()),
        journal.create_file()
    )
