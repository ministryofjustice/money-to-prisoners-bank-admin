from django.conf import settings
from django.urls import reverse_lazy, re_path
from mtp_common.views import GetHelpView as BaseGetHelpView, GetHelpSuccessView


class GetHelpView(BaseGetHelpView):
    success_url = reverse_lazy('feedback_success')
    ticket_subject = 'MTP for digital team - Bank Admin'
    ticket_tags = ['feedback', 'mtp', 'bank-admin', settings.ENVIRONMENT]


urlpatterns = [
    re_path(r'^feedback/$', GetHelpView.as_view(), name='submit_ticket'),
    re_path(r'^feedback/success/$', GetHelpSuccessView.as_view(), name='feedback_success'),
]
