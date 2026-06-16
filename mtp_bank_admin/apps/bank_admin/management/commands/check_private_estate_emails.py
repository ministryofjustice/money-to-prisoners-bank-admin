import logging

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.utils import timezone
from django.utils.dateformat import format as format_date
from django.utils.functional import cached_property
from mtp_common.auth import api_client
from mtp_common.notify import NotifyClient
from mtp_common.stack import StackException, is_first_instance

from bank_admin.disbursements import retrieve_private_estate_batches
from bank_admin.utils import WorkdayChecker, get_start_and_end_date

logger = logging.getLogger('mtp')


class Command(BaseCommand):
    """
    Heartbeat for `send_private_estate_emails`: verifies that every private estate prison which had
    credits for the previous working day actually had its email dispatched via GOV.UK Notify.

    `send_private_estate_emails` runs at 11:00; this is scheduled shortly after. If a prison's email
    is missing it raises, which surfaces in Sentry — rather than relying on the private estate
    noticing and querying that they never received their credits.
    """
    help = 'Checks that private estate credit emails were sent for the previous working day'

    @cached_property
    def api_session(self):
        return api_client.get_authenticated_api_session(
            settings.BANK_ADMIN_USERNAME,
            settings.BANK_ADMIN_PASSWORD,
        )

    def handle(self, **options):
        try:
            should_continue = is_first_instance()
        except StackException:
            should_continue = True
        if not should_continue:
            logger.info('Not checking private estate emails on non-key instance')
            return

        today = timezone.now().date()
        workdays = WorkdayChecker()
        if not workdays.is_workday(today):
            logger.info('Non-workday: no private estate emails to check')
            return
        date = workdays.get_previous_workday(today)

        expected_prisons = self.expected_prisons(date)
        if not expected_prisons:
            logger.info('No private estate batches to check for %s', date)
            return

        notify_client = NotifyClient.shared_client().client
        reference_date = format_date(date, 'Y-m-d')
        missing = []
        for nomis_id in sorted(expected_prisons):
            reference = 'bank-admin-private-csv-%s-%s' % (reference_date, nomis_id)
            response = notify_client.get_all_notifications(reference=reference)
            if not response.get('notifications'):
                missing.append(nomis_id)

        if missing:
            logger.error('Private estate emails not sent for %s: %s', date, missing)
            raise CommandError('Private estate emails not sent for %s: %s' % (date, missing))

        logger.info('Confirmed %d private estate emails sent for %s', len(expected_prisons), date)

    def expected_prisons(self, date):
        start_date, end_date = get_start_and_end_date(date)
        batches = retrieve_private_estate_batches(self.api_session, start_date, end_date)
        # mirrors the batches that `send_private_estate_emails` would actually email:
        # those with credits to send and a configured bank account
        return {
            batch['prison']
            for batch in batches
            if batch.get('total_amount') and batch.get('bank_account')
        }
