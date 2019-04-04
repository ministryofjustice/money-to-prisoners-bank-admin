import codecs
import collections
import csv
import io
import logging
import zipfile

from anymail.message import AnymailMessage
from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.template import loader as template_loader
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.functional import cached_property
from mtp_common.api import retrieve_all_pages_for_path
from mtp_common.auth import api_client
from mtp_common.stack import StackException, is_first_instance

from bank_admin.disbursements import retrieve_private_estate_batches
from bank_admin.utils import WorkdayChecker, format_amount, retrieve_prisons, reconcile_for_date

logger = logging.getLogger('mtp')


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--date', help='Receipt date')
        parser.add_argument('--scheduled', action='store_true')

    @cached_property
    def api_session(self):
        return api_client.get_authenticated_api_session(
            settings.BANK_ADMIN_USERNAME,
            settings.BANK_ADMIN_PASSWORD
        )

    def handle(self, **options):
        date = options['date']
        scheduled = options['scheduled']

        if date and scheduled:
            raise CommandError('Date cannot be provided if running as a scheduled command')

        elif scheduled:
            try:
                should_continue = is_first_instance()
            except StackException:
                should_continue = True
            if not should_continue:
                logger.warning('Not processing private estate emails as running on non-key instance '
                               '(command is not idempotent)')
                return
            today = timezone.now().date()
            workdays = WorkdayChecker()
            if not workdays.is_workday(today):
                logger.info('Non-workday: no private estate batches to process')
                return
            date = workdays.get_previous_workday(today)

        else:
            date = parse_date(date)
            if date is None:
                raise CommandError('Date cannot be parsed, use YYYY-MM-DD format')

        self.process_batches(date)

    def process_batches(self, date):
        start_date, end_date = reconcile_for_date(self.api_session, date)

        batches = retrieve_private_estate_batches(self.api_session, start_date, end_date)
        grouped_batches = combine_private_estate_batches(batches)
        if not grouped_batches:
            logger.info('No private estate batches to handle for %s' % date)
            return

        prisons = retrieve_prisons(self.api_session)
        prisons = {
            nomis_id: prison
            for nomis_id, prison in prisons.items()
            if prison.get('private_estate')
        }

        for prison, batches in grouped_batches.items():
            prison = prisons[prison]
            for batch in batches:
                batch['prison'] = prison
                self.mark_credited(batch)
            csv_contents, total, count = self.prepare_csv(batches)
            send_csv(prison, date, batches, csv_contents, total, count)

    def mark_credited(self, batch):
        self.api_session.patch(
            'private-estate-batches/%s/%s/' % (
                batch['prison']['nomis_id'],
                batch['date'].isoformat(),
            ),
            json={'credited': True}
        )

    def prepare_csv(self, batches):
        f = io.StringIO()
        writer = csv.writer(f, dialect='excel', lineterminator='\r\n', quoting=csv.QUOTE_ALL)
        writer.writerow([
            'Establishment', 'Date', 'Prisoner Name', 'Prisoner Number', 'TransactionID', 'Value', 'Sender', 'Address',
            '',
        ])
        total = 0
        count = 0
        for batch in batches:
            csv_batch_date = batch['date'].strftime('%d/%m/%y')
            credit_list = retrieve_all_pages_for_path(
                self.api_session,
                'private-estate-batches/%s/%s/credits/' % (
                    batch['prison']['nomis_id'],
                    batch['date'].isoformat(),
                )
            )
            count += len(credit_list)
            prison_name = batch['prison'].get('short_name') or batch['prison']['name']
            for credit in credit_list:
                total += credit['amount']
                writer.writerow([
                    prison_name,
                    csv_batch_date,
                    credit['prisoner_name'],
                    credit['prisoner_number'],
                    csv_transaction_id(credit),
                    format_amount(credit['amount']),
                    credit.get('sender_name') or 'Unknown sender',
                    format_address(credit),
                    ''
                ])
        writer.writerow([
            '', '', '', '',
            'Total', format_amount(total),
            '', '', '',
        ])
        return codecs.encode(f.getvalue(), 'cp1252', errors='ignore'), total, count


def combine_private_estate_batches(private_estate_batches):
    batches = collections.defaultdict(list)
    for batch in private_estate_batches:
        if not batch['total_amount']:
            logger.info('Skipping %(prison)s because there are no credits for %(date)s batch' % batch)
            continue
        if not batch.get('bank_account'):
            logger.error('Private estate batch missing bank account %(prison)s %(date)s' % batch)
            continue
        batch['date'] = parse_date(batch['date'])
        batches[batch['prison']].append(batch)
    return batches


def send_csv(prison, date, batches, csv_contents, total, count):
    prison_name = prison.get('short_name') or prison['name']
    some_batch = batches[0]
    now = timezone.now()
    csv_name = 'payment_%s_%s.csv' % (
        prison['cms_establishment_code'],
        now.strftime('%Y%m%d_%H%M%S'),
    )
    zipped_csv = io.BytesIO()
    with zipfile.ZipFile(zipped_csv, 'w') as z:
        z.writestr(csv_name, csv_contents)
    template_context = {
        'prison_name': prison_name,
        'date': date,
        'total': total,
        'count': count,
    }
    from_address = getattr(settings, 'MAILGUN_FROM_ADDRESS', '') or settings.DEFAULT_FROM_EMAIL
    text_body = template_loader.get_template('bank_admin/emails/private-estate.txt').render(template_context)
    html_body = template_loader.get_template('bank_admin/emails/private-estate.html').render(template_context)
    email = AnymailMessage(
        subject='Credits received from "Send money to someone in prison" for %s on %s' % (
            prison_name, date.strftime('%d/%m/%Y'),
        ),
        body=text_body.strip('\n'),
        from_email=from_address,
        to=some_batch['remittance_emails'],
        tags=['private-csv'],
    )
    email.attach_alternative(html_body, mimetype='text/html')
    email.attach(csv_name + '.zip', zipped_csv.getvalue(), mimetype='application/zip')
    email.send()
    logger.info('Sent private estate batch for %s' % prison_name)


def csv_transaction_id(credit):
    """
    Add 100M to MTP credit id to avoid clash with SPS transaction id
    SPS transaction ids are approaching 2M as of 2019
    """
    return credit['id'] + 100000000


def format_address(credit):
    if credit['source'] == 'bank_transfer':
        return 'Bank Transfer 102 Petty France London SW1H 9AJ'
    billing_address = credit.get('billing_address')
    if not billing_address:
        return 'Missing Address 102 Petty France London SW1H 9AJ'
    return ' '.join(filter(None, (
        billing_address.get(key)
        for key in ('line1', 'line2', 'city', 'postcode', 'country')
    )))
