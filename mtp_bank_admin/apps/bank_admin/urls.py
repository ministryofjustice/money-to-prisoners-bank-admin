from urllib.parse import urljoin

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.urls import re_path
from django.views.generic import RedirectView

from . import views

app_name = 'bank_admin'
urlpatterns = [
    re_path(r'^$', login_required(views.DashboardView.as_view()), name='dashboard'),

    re_path(r'^refund_pending/download/$', views.download_refund_file, name='download_refund_file'),
    re_path(r'^adi/download/$', views.download_adi_journal, name='download_adi_journal'),
    re_path(r'^bank_statement/download/$', views.download_bank_statement, name='download_bank_statement'),
    re_path(r'^disbursements/download/$', views.download_disbursements, name='download_disbursements'),

    re_path(r'^q_and_a/$', RedirectView.as_view(url=urljoin(settings.SEND_MONEY_URL, '/help/faq/'), permanent=True)),
]
