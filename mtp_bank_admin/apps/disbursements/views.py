import datetime
from math import ceil

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _, gettext
from django.views.generic import FormView, TemplateView
from mtp_common.api import retrieve_all_pages_for_path
from mtp_common.auth.api_client import get_api_session
from openpyxl import Workbook

from .templatetags.disbursements import currency
from .forms import ChooseDisbursementForm, CancelDisbursementForm


class CancelDisbursementView(FormView):
    template_name = 'disbursements/cancel.html'
    form_class = ChooseDisbursementForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def form_valid(self, form):
        return HttpResponseRedirect(
            reverse_lazy(
                'disbursements:cancel-disbursement-confirm',
                kwargs={'invoice_number': form.cleaned_data['invoice_number']}
            )
        )


class ConfirmCancelDisbursementView(FormView):
    template_name = 'disbursements/confirm.html'
    form_class = CancelDisbursementForm
    success_url = reverse_lazy('disbursements:cancel-disbursement')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = get_api_session(self.request)

        disbursement = session.get(
            '/disbursements/',
            params={
                'invoice_number': self.kwargs['invoice_number'],
            }
        ).json()
        if disbursement['count'] != 1:
            raise Http404
        context['disbursement'] = disbursement['results'][0]
        return context

    def form_valid(self, form):
        form.cancel_disbursement()
        if form.is_valid():
            messages.add_message(
                self.request,
                messages.SUCCESS,
                _('Cancelled disbursement {invoice_number}').format(
                    invoice_number=form.disbursement['invoice_number']
                )
            )
            return super().form_valid(form)
        context = self.get_context_data(form=form)
        return self.render_to_response(context)


class CancelledDisbursementsView(TemplateView):
    template_name = 'disbursements/cancelled.html'
    page_size = 20

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        session = get_api_session(self.request)

        page = int(self.request.GET.get('page', 1))
        offset = (page - 1) * self.page_size
        cancelled_disbursements = session.get(
            '/disbursements/',
            params={
                'ordering': '-log__created',
                'log__action': 'cancelled',
                'resolution': 'cancelled',
                'offset': offset,
                'limit': self.page_size
            }
        ).json()
        count = cancelled_disbursements.get('count', 0)
        context['page_count'] = int(ceil(count / self.page_size))
        context['page'] = page
        context['cancelled_disbursements'] = cancelled_disbursements['results']
        return context


def export_cancelled_disbursements(request, *args, **kwargs):
    session = get_api_session(request)
    cancelled_disbursements = retrieve_all_pages_for_path(
        session, 'disbursements/', **{
            'ordering': '-log__created',
            'log__action': 'cancelled',
            'resolution': 'cancelled',
        }
    )

    return ObjectListXlsxResponse(cancelled_disbursements)


class ObjectListXlsxResponse(HttpResponse):
    def __init__(self, object_list, attachment_name='export.xlsx', **kwargs):
        kwargs.setdefault(
            'content_type',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        super().__init__(**kwargs)
        self['Content-Disposition'] = 'attachment; filename="%s"' % attachment_name
        workbook = Workbook(write_only=True)
        worksheet = workbook.create_sheet()
        for row in disbursement_row_generator(object_list):
            worksheet.append([escape_formulae(cell) for cell in row])
        workbook.save(self)


def escape_formulae(value):
    """
    Escapes formulae (strings that start with =) to prevent
    spreadsheet software vulnerabilities being exploited
    :param value: the value being added to a CSV cell
    """
    if isinstance(value, str) and value.startswith('='):
        return "'" + value
    if isinstance(value, datetime.datetime):
        return value.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(value, datetime.date):
        return value.strftime('%Y-%m-%d')
    return value


def disbursement_row_generator(object_list):
    yield [
        gettext('Invoice number'),
        gettext('Amount'),
        gettext('Created'),
        gettext('Cancelled'),
        gettext('Cancelled by'),
        gettext('Notes'),
    ]
    for disbursement in object_list:
        log_actions = {}
        for log_item in disbursement['log_set']:
            log_item['created'] = parse_datetime(log_item['created'])
            log_actions[log_item['action']] = log_item
        yield [
            disbursement['invoice_number'],
            currency(int(disbursement['amount'])),
            log_actions['confirmed']['created'],
            log_actions['cancelled']['created'],
            ' '.join([
                log_actions['cancelled']['user']['first_name'],
                log_actions['cancelled']['user']['last_name']
            ]),
            ', '.join([
                comment['comment'] for comment in disbursement['comments']
                if comment['category'] == 'cancel'
            ]),
        ]
