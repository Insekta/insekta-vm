from django.contrib import admin

from insektavm.vm.models import VMTemplate, ActiveVMResource, VirtualMachine


admin.site.register(VMTemplate)
admin.site.register(ActiveVMResource)
admin.site.register(VirtualMachine)