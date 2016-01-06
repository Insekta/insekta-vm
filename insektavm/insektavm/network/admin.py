from django.contrib import admin

from insektavm.network.models import Network, NetworkRange


class NetworkRangeAdmin(admin.ModelAdmin):
    list_display = ['name', 'network', 'subnet_prefix']
    ordering = ['name']


class NetworkAdmin(admin.ModelAdmin):
    list_display = ['network', 'range', 'in_use']


admin.site.register(Network, NetworkAdmin)
admin.site.register(NetworkRange, NetworkRangeAdmin)