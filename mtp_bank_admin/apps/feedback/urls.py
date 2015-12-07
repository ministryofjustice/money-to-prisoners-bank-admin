from django.conf.urls import url
from zendesk_tickets import views

urlpatterns = [
    url(r'^feedback/$', views.ticket,
        {
            'template_name': 'feedback/submit_feedback.html',
            'success_redirect_url': '',
            'subject': 'MTP Bank Admin Feedback',
            'tags': ['feedback', 'mtp', 'bank-admin']
        }, name='submit_ticket'),
]
