from datetime import datetime
from functools import wraps

from django.contrib import messages
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.translation import gettext as _

from .exceptions import EmptyFileError, EarlyReconciliationError, UpstreamServiceUnavailable


def filter_by_receipt_date(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        receipt_date = None
        receipt_date_str = request.GET.get('receipt_date')
        if receipt_date_str:
            try:
                receipt_date = datetime.strptime(receipt_date_str, '%Y-%m-%d').date()
            except ValueError:
                return HttpResponseBadRequest(_('Invalid format for receipt_date'))
        else:
            return HttpResponseBadRequest(_("'receipt_date' parameter required"))
        return view_func(request, receipt_date, *args, **kwargs)
    return wrapper


def handle_file_download_errors(view_func):
    @wraps(view_func)
    def wrapper(request, receipt_date, *args, **kwargs):
        try:
            return view_func(request, receipt_date, *args, **kwargs)
        except EmptyFileError:
            messages.add_message(request, messages.ERROR, _(
                'No transactions available'))
        except EarlyReconciliationError:
            messages.add_message(request, messages.ERROR, _(
                'This file cannot be downloaded until the next working day'))
        except UpstreamServiceUnavailable:
            messages.add_message(request, messages.ERROR, _(
                'There was a problem generating the file. Please try again later.'))
        return redirect(reverse_lazy('bank_admin:dashboard'))
    return wrapper
