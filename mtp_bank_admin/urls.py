from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.http import HttpResponse
from django.template.response import TemplateResponse
from django.urls import include, reverse_lazy, re_path
from django.views.decorators.cache import cache_control
from django.views.generic import RedirectView
from django.views.i18n import JavaScriptCatalog
from moj_irat.views import HealthcheckView, PingJsonView
from mtp_common.auth import views as auth_views
from mtp_common.metrics.views import metrics_view
from mtp_common.views import SettingsView

urlpatterns = i18n_patterns(
    re_path(
        r'^login/$', auth_views.login, {
            'template_name': 'mtp_auth/login.html',
        }, name='login'
    ),
    re_path(
        r'^logout/$', auth_views.logout, {
            'template_name': 'mtp_auth/login.html',
            'next_page': reverse_lazy('login'),
        }, name='logout'
    ),


    re_path(
        r'^settings/$',
        SettingsView.as_view(),
        name='settings'
    ),
    re_path(
        r'^password_change/$', auth_views.password_change, {
            'template_name': 'mtp_common/auth/password_change.html',
            'cancel_url': reverse_lazy('settings'),
        }, name='password_change'
    ),
    re_path(
        r'^create_password/$', auth_views.password_change_with_code, {
            'template_name': 'mtp_common/auth/password_change_with_code.html',
            'cancel_url': reverse_lazy('bank_admin:dashboard'),
        }, name='password_change_with_code'
    ),
    re_path(
        r'^password_change_done/$', auth_views.password_change_done, {
            'template_name': 'mtp_common/auth/password_change_done.html',
            'cancel_url': reverse_lazy('bank_admin:dashboard'),
        }, name='password_change_done'
    ),
    re_path(
        r'^reset-password/$', auth_views.reset_password, {
            'password_change_url': reverse_lazy('password_change_with_code'),
            'template_name': 'mtp_common/auth/reset-password.html',
            'cancel_url': reverse_lazy('bank_admin:dashboard'),
        }, name='reset_password'
    ),
    re_path(
        r'^reset-password-done/$', auth_views.reset_password_done, {
            'template_name': 'mtp_common/auth/reset-password-done.html',
            'cancel_url': reverse_lazy('bank_admin:dashboard'),
        }, name='reset_password_done'
    ),
    re_path(
        r'^email_change/$', auth_views.email_change, {
            'cancel_url': reverse_lazy('settings'),
        }, name='email_change'
    ),

    re_path(r'^', include('bank_admin.urls', namespace='bank_admin',)),
    re_path(r'^', include('feedback.urls')),
    re_path(r'^', include('mtp_common.user_admin.urls')),

    re_path(r'^js-i18n.js$', cache_control(public=True, max_age=86400)(JavaScriptCatalog.as_view()), name='js-i18n'),

    re_path(r'^404.html$', lambda request: TemplateResponse(request, 'mtp_common/errors/404.html', status=404)),
    re_path(r'^500.html$', lambda request: TemplateResponse(request, 'mtp_common/errors/500.html', status=500)),
)

urlpatterns += [
    re_path(r'^ping.json$', PingJsonView.as_view(
        build_date_key='APP_BUILD_DATE',
        commit_id_key='APP_GIT_COMMIT',
        version_number_key='APP_BUILD_TAG',
    ), name='ping_json'),
    re_path(r'^healthcheck.json$', HealthcheckView.as_view(), name='healthcheck_json'),
    re_path(r'^metrics.txt$', metrics_view, name='prometheus_metrics'),

    re_path(r'^favicon.ico$', RedirectView.as_view(url=settings.STATIC_URL + 'images/favicon.ico', permanent=True)),
    re_path(r'^robots.txt$', lambda request: HttpResponse('User-agent: *\nDisallow: /', content_type='text/plain')),
    re_path(r'^\.well-known/security\.txt$', RedirectView.as_view(
        url='https://security-guidance.service.justice.gov.uk/.well-known/security.txt',
        permanent=True,
    )),
]

handler404 = 'mtp_common.views.page_not_found'
handler500 = 'mtp_common.views.server_error'
handler400 = 'mtp_common.views.bad_request'
