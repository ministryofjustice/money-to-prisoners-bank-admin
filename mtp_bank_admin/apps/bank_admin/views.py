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
from .exceptions import EmptyFileError, EarlyReconciliationError

logger = logging.getLogger('mtp')


@login_required
@filter_by_receipt_date
def download_refund_file(request, receipt_date):
    try:
        filename, csvdata = refund.generate_refund_file_for_date(request, receipt_date)
        logger.info('User "%(username)s" is downloading AccessPay file for %(date)s' % {
            'username': request.user.username,
            'date': date_format(receipt_date, 'Y-m-d'),
        })

        response = HttpResponse(csvdata, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR, _('No transactions available'))
    except EarlyReconciliationError:
        messages.add_message(request, messages.ERROR, _('This file cannot be downloaded until the next working day'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


@login_required
@filter_by_receipt_date
def download_adi_journal(request, receipt_date):
    try:
        filename, filedata = adi.generate_adi_journal(request, receipt_date)
        file_description = 'ADI journal'

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
        messages.add_message(request, messages.ERROR, _('No transactions available'))
    except EarlyReconciliationError:
        messages.add_message(request, messages.ERROR, _('This file cannot be downloaded until the next working day'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


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
        messages.add_message(request, messages.ERROR, _('No transactions available'))
    except EarlyReconciliationError:
        messages.add_message(request, messages.ERROR, _('This file cannot be downloaded until the next working day'))
    return redirect(reverse_lazy('bank_admin:dashboard'))
