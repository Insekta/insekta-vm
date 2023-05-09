from django.urls import path

from insektavm.vpn import views


urlpatterns = [
    path('assign', views.api_assign_ip, name='api_vm_start'),
    path('unassign', views.api_unassign_ip, name='api_vm_stop'),
]
