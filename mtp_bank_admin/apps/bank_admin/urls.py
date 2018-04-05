from django.contrib.auth.decorators import login_required
from django.conf.urls import url
from django.views.generic.base import TemplateView

from . import views

app_name = 'bank_admin'
urlpatterns = [
    url(r'^$', login_required(views.DashboardView.as_view()), name='dashboard'),

    url(r'^refund_pending/download/$', views.download_refund_file, name='download_refund_file'),
    url(r'^adi/download/$', views.download_adi_journal, name='download_adi_journal'),
    url(r'^bank_statement/download/$', views.download_bank_statement, name='download_bank_statement'),
    url(r'^disbursements/download/$', views.download_disbursements, name='download_disbursements'),

    url(r'^q_and_a/$', TemplateView.as_view(template_name='faq.html'), name='faq')
]
