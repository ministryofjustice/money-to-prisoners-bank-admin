from datetime import date
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.dateformat import format as date_format
from mtp_common.auth.api_client import get_api_session

from . import refund, adi, statement, disbursements
from .decorators import filter_by_receipt_date, handle_file_download_errors

logger = logging.getLogger('mtp')


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_refund_file(request, receipt_date):
    csvfile = refund.get_refund_file(
        get_api_session(request), receipt_date, mark_refunded=True
    )
    filename = settings.REFUND_OUTPUT_FILENAME.format(date=date.today())

    response = HttpResponse(csvfile, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    logger.info('User "%(username)s" is downloading AccessPay file for %(date)s' % {
        'username': request.user.username,
        'date': date_format(receipt_date, 'Y-m-d'),
    })

    return response


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_adi_journal(request, receipt_date):
    filedata = adi.get_adi_journal_file(
        get_api_session(request), receipt_date, user=request.user
    )
    filename = settings.ADI_OUTPUT_FILENAME.format(
        initials=request.user.get_initials(),
        date=date.today()
    )

    response = HttpResponse(
        filedata,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    logger.info('User "%(username)s" is downloading ADI journal for %(date)s' % {
        'username': request.user.username,
        'date': date_format(receipt_date, 'Y-m-d'),
    })

    return response


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_bank_statement(request, receipt_date):
    bai2file = statement.get_bank_statement_file(
        get_api_session(request), receipt_date
    )
    filename = settings.BANK_STMT_OUTPUT_FILENAME.format(
        account_number=settings.BANK_STMT_ACCOUNT_NUMBER, date=receipt_date
    )

    response = HttpResponse(bai2file, content_type='application/octet-stream')
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
    filedata = disbursements.get_disbursements_file(
        get_api_session(request), receipt_date, mark_sent=True
    )
    filename = settings.DISBURSEMENT_OUTPUT_FILENAME.format(date=receipt_date)

    response = HttpResponse(
        filedata,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    logger.info('User "%(username)s" is downloading Disbursements for %(date)s' % {
        'username': request.user.username,
        'date': date_format(receipt_date, 'Y-m-d'),
    })

    return response
