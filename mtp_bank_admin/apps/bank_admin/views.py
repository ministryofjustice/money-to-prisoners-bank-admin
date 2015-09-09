from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect
from django.core.urlresolvers import reverse_lazy
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from . import refund
from .exceptions import EmptyFileError
from . import adi
from .types import PaymentType


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
    except:
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
    except:
        messages.add_message(request, messages.ERROR,
                             _('Could not download ADI file'))
    return redirect(reverse_lazy('bank_admin:dashboard'))


@login_required
def download_adi_payment_file(request):
    return download_adi_file(PaymentType.payment, request)


@login_required
def download_adi_refund_file(request):
    return download_adi_file(PaymentType.refund, request)
