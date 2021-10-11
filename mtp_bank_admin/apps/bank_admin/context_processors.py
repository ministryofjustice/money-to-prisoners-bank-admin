from django.conf import settings


def bank_admin_settings(_):
    return {
        'footer_feedback_link': settings.FOOTER_FEEDBACK_LINK,
    }
