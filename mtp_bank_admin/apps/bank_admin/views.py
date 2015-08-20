from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from . import refund


@login_required
def download_refund_file(request):
    filename, csvdata = refund.generate_refund_file(request)

    response = HttpResponse(csvdata, content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="%s"' % filename

    return response
