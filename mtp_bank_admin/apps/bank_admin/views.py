import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.dateformat import format as date_format

from . import refund, adi, statement, disbursements
from .decorators import filter_by_receipt_date, handle_file_download_errors

logger = logging.getLogger('mtp')


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_refund_file(request, receipt_date):
    filename, csvdata = refund.generate_refund_file_for_date(request, receipt_date)
    logger.info('User "%(username)s" is downloading AccessPay file for %(date)s' % {
        'username': request.user.username,
        'date': date_format(receipt_date, 'Y-m-d'),
    })

    response = HttpResponse(csvdata, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    return response


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_adi_journal(request, receipt_date):
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


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_bank_statement(request, receipt_date):
    filename, bai2 = statement.generate_bank_statement(request, receipt_date)

    response = HttpResponse(bai2, content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    logger.info('User "%(username)s" is downloading bank statement file for %(date)s' % {
        'username': request.user.username,
        'date': date_format(receipt_date, 'Y-m-d'),
    })

    return response


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_disbursements(request, receipt_date):
    filename, filedata = disbursements.generate_disbursements_journal(
        request, receipt_date
    )
    file_description = 'Disbursements'

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
