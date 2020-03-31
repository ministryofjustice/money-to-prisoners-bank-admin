from django.conf import settings
from django.conf.urls import url
from django.core.urlresolvers import reverse_lazy
from mtp_common.views import GetHelpView as BaseGetHelpView, GetHelpSuccessView


class GetHelpView(BaseGetHelpView):
    success_url = reverse_lazy('feedback_success')
    ticket_subject = 'MTP for digital team - Bank Admin'
    ticket_tags = ['feedback', 'mtp', 'bank-admin', settings.ENVIRONMENT]


urlpatterns = [
    url(r'^feedback/$', GetHelpView.as_view(), name='submit_ticket'),
    url(r'^feedback/success/$', GetHelpSuccessView.as_view(), name='feedback_success'),
]
