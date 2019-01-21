from django.contrib.auth.decorators import login_required
from django.conf.urls import url

from . import views

urlpatterns = [
    url(
        r'^cancel-disbursement/$',
        login_required(views.CancelDisbursementListView.as_view()),
        name='cancel-disbursement-list'
    ),
    url(
        r'^cancel-disbursement/(?P<invoice_number>.+)/$',
        login_required(views.CancelDisbursementView.as_view()),
        name='cancel-disbursement'
    ),
]
