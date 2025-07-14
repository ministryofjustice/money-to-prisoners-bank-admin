from django.conf import settings
from django.utils.translation import gettext


def bank_admin_settings(_):
    return {
        'proposition_title': gettext('Bank admin'),
        'footer_feedback_link': settings.FOOTER_FEEDBACK_LINK,
    }
