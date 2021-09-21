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
This link contains the details of credits received for ((prison_name))
on ((date)) from ‘Send money to someone in prison’.

((attachment))

* Click on the link to download the file
* Upload it to your CMS
* Make sure that no credits are rejected
* You don’t have to send a response email to Secure Payment Service

If you have any doubts, you should put the credits on hold or contact your security department.
            """).strip(),
            'personalisation': [
                'prison_name', 'date',
                'attachment',
            ],
        },
    }
