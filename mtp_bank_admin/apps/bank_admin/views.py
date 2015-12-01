import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from . import refund, adi, statement
from .decorators import filter_by_receipt_date
from .exceptions import EmptyFileError
from .types import PaymentType

logger = logging.getLogger(__name__)


@login_required
def download_refund_file(request):
    try:
        filename, csvdata = refund.generate_new_refund_file(request)

        response = HttpResponse(csvdata, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available for refund'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


@login_required
def download_previous_refund_file(request):
    try:
        filename, csvdata = refund.generate_previous_refund_file(request)

        response = HttpResponse(csvdata, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No previously refunded transactions found'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


def download_adi_file(payment_type, request, receipt_date):
    try:
        if payment_type == PaymentType.payment:
            filename, filedata = adi.generate_adi_payment_file(request, receipt_date)
        else:
            filename, filedata = adi.generate_adi_refund_file(request, receipt_date)

        response = HttpResponse(
            filedata,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available for reconciliation'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


@login_required
@filter_by_receipt_date
def download_adi_payment_file(request, receipt_date):
    return download_adi_file(PaymentType.payment, request, receipt_date)


@login_required
@filter_by_receipt_date
def download_adi_refund_file(request, receipt_date):
    return download_adi_file(PaymentType.refund, request, receipt_date)


@login_required
@filter_by_receipt_date
def download_bank_statement(request, receipt_date):
    try:
        filename, bai2 = statement.generate_bank_statement(request, receipt_date)

        response = HttpResponse(bai2, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available on account'))
    return redirect(reverse_lazy('bank_admin:dashboard'))
