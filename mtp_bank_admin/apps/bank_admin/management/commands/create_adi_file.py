from bank_admin.adi import get_adi_journal_file
from . import FileGenerationCommand


class Command(FileGenerationCommand):
    function = get_adi_journal_file
