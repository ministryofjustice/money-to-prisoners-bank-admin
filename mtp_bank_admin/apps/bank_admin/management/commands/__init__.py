import logging
from datetime import date

from django.conf import settings
from django.core.management import BaseCommand, CommandError
from django.utils.dateparse import parse_date
from mtp_common.auth import api_client

from bank_admin.utils import WorkdayChecker

logger = logging.getLogger('mtp')


class FileGenerationCommand(BaseCommand):
    function = NotImplemented

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--date', dest='date', type=str, help='Receipt date')

    def handle(self, *args, **options):
        if settings.CLOUD_PLATFORM_MIGRATION_MODE:
            logger.warning(f'{self.__class__.__module__} management command will not run in migration mode')
            return

        if options['date']:
            receipt_date = parse_date(options['date'])
            if not receipt_date:
                raise CommandError('Date %s cannot be parsed, use YYYY-MM-DD format' % date)
        else:
            workdays = WorkdayChecker()
            if not workdays.is_workday(date.today()):
                return
            receipt_date = workdays.get_previous_workday(date.today())

        api_session = api_client.get_authenticated_api_session(
            settings.BANK_ADMIN_USERNAME,
            settings.BANK_ADMIN_PASSWORD
        )
        self.__class__.function(api_session, receipt_date)
