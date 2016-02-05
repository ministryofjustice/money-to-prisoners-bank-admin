import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.utils.dateformat import format as date_format
from django.utils.translation import ugettext_lazy as _

from . import refund, adi, statement
from .decorators import filter_by_receipt_date
from .exceptions import EmptyFileError
from .types import PaymentType

logger = logging.getLogger('mtp')


@login_required
def download_refund_file(request):
    redownload_refunds = request.GET.get('redownload_refunds', False)
    try:
        try:
            filename, csvdata = refund.generate_new_refund_file(request)
            logger.info('User "%s" is downloading latest refund file' % request.user.username)
        except EmptyFileError:
            if redownload_refunds:
                filename, csvdata = refund.generate_previous_refund_file(request)
                logger.info('User "%(username)s" is downloading previous refund file' % {
                    'username': request.user.username
                })
            else:
                raise EmptyFileError

        response = HttpResponse(csvdata, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        if redownload_refunds:
            messages.add_message(request, messages.ERROR,
                                 _('No transactions available for refund'))

    return redirect(reverse_lazy('bank_admin:dashboard') + '?redownload_refunds=true')


def download_adi_file(payment_type, request, receipt_date):
    try:
        if payment_type == PaymentType.payment:
            filename, filedata = adi.generate_adi_payment_file(request, receipt_date)
            file_description = 'ADI payment file'
        else:
            filename, filedata = adi.generate_adi_refund_file(request, receipt_date)
            file_description = 'ADI refund file'

        response = HttpResponse(
            filedata,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        logger.info('User "%(username)s" is downloading %(file_description)s for %(date)s' % {
            'username': request.user.username,
            'file_description': file_description,
            'date': date_format(receipt_date, 'Y-m-d'),
        })

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

        logger.info('User "%(username)s" is downloading bank statement file for %(date)s' % {
            'username': request.user.username,
            'date': date_format(receipt_date, 'Y-m-d'),
        })

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available on account'))
    return redirect(reverse_lazy('bank_admin:dashboard'))
