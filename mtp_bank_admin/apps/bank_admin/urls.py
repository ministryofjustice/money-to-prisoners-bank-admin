from urllib.parse import urljoin

from django.conf import settings
from django.conf.urls import url
from django.contrib.auth.decorators import login_required
from django.views.generic import RedirectView

from . import views

app_name = 'bank_admin'
urlpatterns = [
    url(r'^$', login_required(views.DashboardView.as_view()), name='dashboard'),

    url(r'^refund_pending/download/$', views.download_refund_file, name='download_refund_file'),
    url(r'^adi/download/$', views.download_adi_journal, name='download_adi_journal'),
    url(r'^bank_statement/download/$', views.download_bank_statement, name='download_bank_statement'),
    url(r'^disbursements/download/$', views.download_disbursements, name='download_disbursements'),

    url(r'^q_and_a/$', RedirectView.as_view(url=urljoin(settings.SEND_MONEY_URL, '/help/faq/'), permanent=True)),
]
