from django.conf.urls import url

from insektavm.vpn import views


urlpatterns = [
    url(r'^assign$', views.api_assign_ip, name='api_vm_start'),
    url(r'^unassign$', views.api_unassign_ip, name='api_vm_stop'),
]