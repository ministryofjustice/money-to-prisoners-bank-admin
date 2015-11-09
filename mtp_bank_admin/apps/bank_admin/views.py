import logging

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from . import refund, adi, statement
from .exceptions import EmptyFileError
from .types import PaymentType

logger = logging.getLogger(__name__)


@login_required
def download_refund_file(request):
    try:
        filename, csvdata = refund.generate_refund_file(request)

        response = HttpResponse(csvdata, content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available for refund'))
    except Exception as e:
        logger.exception(e)
        messages.add_message(request, messages.ERROR,
                             _('Could not download AccessPay file'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


def download_adi_file(payment_type, request):
    try:
        if payment_type == PaymentType.payment:
            filename, filedata = adi.generate_adi_payment_file(request)
        else:
            filename, filedata = adi.generate_adi_refund_file(request)

        response = HttpResponse(
            filedata,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available for reconciliation'))
    except Exception as e:
        logger.exception(e)
        messages.add_message(request, messages.ERROR,
                             _('Could not download ADI file'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


@login_required
def download_adi_payment_file(request):
    return download_adi_file(PaymentType.payment, request)


@login_required
def download_adi_refund_file(request):
    return download_adi_file(PaymentType.refund, request)


@login_required
def download_bank_statement(request):
    try:
        filename, bai2 = statement.generate_bank_statement(request)

        response = HttpResponse(bai2, content_type='text/plain')
        response['Content-Disposition'] = 'attachment; filename="%s"' % filename

        return response
    except EmptyFileError:
        messages.add_message(request, messages.ERROR,
                             _('No new transactions available on account'))
    except Exception as e:
        logger.exception(e)
        messages.add_message(request, messages.ERROR,
                             _('Could not download BAI2 bank statement'))
    return redirect(reverse_lazy('bank_admin:dashboard'))
