import shutil

from django.core.management import BaseCommand


class Command(BaseCommand):

    def handle(self, *args, **options):
        shutil.rmtree('local_files/cache/', ignore_errors=True)
