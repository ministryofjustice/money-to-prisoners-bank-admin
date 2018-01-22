from bank_admin.disbursements import get_disbursements_file
from . import FileGenerationCommand


class Command(FileGenerationCommand):
    function = get_disbursements_file
