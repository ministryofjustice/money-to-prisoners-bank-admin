from datetime import datetime
from functools import wraps

from django.http import HttpResponseBadRequest
from django.utils.translation import ugettext as _


def filter_by_receipt_date(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        receipt_date = None
        receipt_date_str = request.GET.get('receipt_date')
        if receipt_date_str:
            try:
                receipt_date = datetime.strptime(receipt_date_str, '%Y-%m-%d')
            except ValueError:
                return HttpResponseBadRequest(_("Invalid format for receipt_date"))
        return view_func(request, receipt_date, *args, **kwargs)
    return wrapper
