from django.conf.urls import include, url

urlpatterns = [
    url(r'^auth/', include('mtp_auth.urls', namespace='auth',)),
    url(r'^', include('bank_admin.urls', namespace='bank_admin',)),
]
