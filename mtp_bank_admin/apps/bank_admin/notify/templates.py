import textwrap

from mtp_common.notify.templates import NotifyTemplateRegistry


class BankAdminNotifyTemplates(NotifyTemplateRegistry):
    """
    Templates that mtp-bank-admin expects to exist in GOV.UK Notify
    """
    templates = {
        'bank-admin-private-csv': {
            'subject': 'Credits received from ‘Send money to someone in prison’ for ((prison_name)) on ((date))',
            'body': textwrap.dedent("""
These credits were received for ((prison_name)) on ((date)) from ‘Send money to someone in prison’.

Please download this file and upload into the CMS:
((attachment))

Make sure NO credits are rejected.

If there’s any doubt, put credits on hold or speak with your security department.

Once all credits are accepted, make sure you DON’T send the response email to Secure Payment Service.
            """).strip(),
            'personalisation': [
                'prison_name', 'date',
                'attachment',
            ],
        },
    }
