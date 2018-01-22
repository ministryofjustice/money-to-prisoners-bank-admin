from bank_admin.refund import get_refund_file
from . import FileGenerationCommand


class Command(FileGenerationCommand):
    function = get_refund_file
