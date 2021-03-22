from datetime import date
import logging

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils.dateformat import format as date_format
from django.utils.dateparse import parse_date
from django.views.generic.base import TemplateView
from mtp_common.auth.api_client import get_api_session
from mtp_common.auth.exceptions import HttpClientError

from . import (
    refund, adi, statement, disbursements, ADI_JOURNAL_LABEL, ACCESSPAY_LABEL,
    MT940_STMT_LABEL, DISBURSEMENTS_LABEL
)
from .decorators import filter_by_receipt_date, handle_file_download_errors
from .exceptions import EmptyFileError
from .utils import get_preceding_workday_list

logger = logging.getLogger('mtp')


def record_download(api_session, label, receipt_date):
    try:
        api_session.post(
            'file-downloads/',
            json={
                'label': label,
                'date': receipt_date.isoformat()
            }
        )
    except HttpClientError:
        pass  # expected non-unique error if re-downloading


def get_missing_downloads(api_session, label, dates):
    response = api_session.get(
        'file-downloads/missing/',
        params={
            'label': label,
            'date': dates
        }
    )
    return [parse_date(date) for date in response.json()['missing_dates']]


class DashboardView(TemplateView):
    template_name = 'bank_admin/dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        preceding_workdays = get_preceding_workday_list(5, offset=1)
        context['latest_day'], context['preceding_days'] = preceding_workdays[0], preceding_workdays[1:]

        api_session = get_api_session(self.request)
        workday_list = get_preceding_workday_list(20, offset=2)
        user = self.request.user
        if user.has_perm('transaction.view_bank_details_transaction'):
            context['missed_refunds'] = get_missing_downloads(
                api_session, ACCESSPAY_LABEL, workday_list
            )
        if user.has_perm('credit.view_any_credit'):
            context['missed_adi_journals'] = get_missing_downloads(
                api_session, ADI_JOURNAL_LABEL, workday_list
            )
        if user.has_perm('transaction.view_transaction'):
            context['missed_statements'] = get_missing_downloads(
                api_session, MT940_STMT_LABEL, workday_list
            )
        if user.has_perm('disbursement.view_disbursement'):
            context['missed_disbursements'] = get_missing_downloads(
                api_session, DISBURSEMENTS_LABEL, workday_list
            )

        context['show_access_pay_refunds'] = settings.SHOW_ACCESS_PAY_REFUNDS
        return context


@login_required
@filter_by_receipt_date
@handle_file_download_errors
def download_refund_file(request, receipt_date):
    api_session = get_api_session(request)
    try:
        csvfile = refund.get_refund_file(
            api_session, receipt_date, mark_refunded=True
        )
        record_download(api_session, ACCESSPAY_LABEL, receipt_date)
    except EmptyFileError as e:
        record_download(api_session, ACCESSPAY_LABEL, receipt_date)
        raise e

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
    api_session = get_api_session(request)
    try:
        filedata = adi.get_adi_journal_file(
            api_session, receipt_date, user=request.user
        )
        record_download(api_session, ADI_JOURNAL_LABEL, receipt_date)
    except EmptyFileError as e:
        record_download(api_session, ADI_JOURNAL_LABEL, receipt_date)
        raise e

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
    api_session = get_api_session(request)
    try:
        bai2file = statement.get_bank_statement_file(api_session, receipt_date)
        record_download(api_session, MT940_STMT_LABEL, receipt_date)
    except EmptyFileError as e:
        record_download(api_session, MT940_STMT_LABEL, receipt_date)
        raise e

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
    api_session = get_api_session(request)
    try:
        filedata = disbursements.get_disbursements_file(
            api_session, receipt_date, mark_sent=True
        )
        record_download(api_session, DISBURSEMENTS_LABEL, receipt_date)
    except EmptyFileError as e:
        record_download(api_session, DISBURSEMENTS_LABEL, receipt_date)
        raise e

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
