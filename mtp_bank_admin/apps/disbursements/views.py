from math import ceil

from django.contrib import messages
from django.core.urlresolvers import reverse_lazy
from django.http import HttpResponseRedirect, Http404
from django.utils.translation import gettext_lazy as _
from django.views.generic import FormView
from mtp_common.auth.api_client import get_api_session

from .forms import ChooseDisbursementForm, CancelDisbursementForm


class CancelDisbursementListView(FormView):
    template_name = 'disbursements/cancelled.html'
    form_class = ChooseDisbursementForm
    page_size = 20

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['request'] = self.request
        return kwargs

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

    def form_valid(self, form):
        return HttpResponseRedirect(
            reverse_lazy(
                'disbursements:cancel-disbursement',
                kwargs={'invoice_number': form.cleaned_data['invoice_number']}
            )
        )


class CancelDisbursementView(FormView):
    template_name = 'disbursements/cancel.html'
    form_class = CancelDisbursementForm
    success_url = reverse_lazy('disbursements:cancel-disbursement-list')

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
                self.request, messages.SUCCESS, _('Disbursement cancelled')
            )
            return super().form_valid(form)
        context = self.get_context_data(form=form)
        return self.render_to_response(context)
