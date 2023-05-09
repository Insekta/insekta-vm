from django.urls import path

from insektavm.vm import views


urlpatterns = [
    path('start', views.api_start_vm, name='api_vm_start'),
    path('stop', views.api_stop_vm, name='api_vm_stop'),
    path('ping', views.api_ping_vm, name='api_vm_ping'),
    path('status', views.api_get_vm_status, name='api_get_vm_status')
]
