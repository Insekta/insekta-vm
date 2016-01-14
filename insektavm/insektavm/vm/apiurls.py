from django.conf.urls import url

from insektavm.vm import views


urlpatterns = [
    url(r'^start$', views.api_start_vm, name='api_vm_start'),
    url(r'^stop$', views.api_stop_vm, name='api_vm_stop'),
    url(r'^ping$', views.api_ping_vm, name='api_vm_ping'),
    url(r'^status$', views.api_get_vm_status, name='api_get_vm_status')
]