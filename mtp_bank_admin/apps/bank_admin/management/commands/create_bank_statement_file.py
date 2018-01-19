from bank_admin.statement import get_bank_statement_file
from . import FileGenerationCommand


class Command(FileGenerationCommand):
    function = get_bank_statement_file
