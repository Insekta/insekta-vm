import os

from django.contrib import admin, messages
from django.conf import settings
from django.shortcuts import render, redirect
from django import forms

from insektavm.resources.models import Resource
from insektavm.vm.models import VMTemplate, ActiveVMResource, VirtualMachine


class VMTemplateAdmin(admin.ModelAdmin):
    def add_view(self, request, form_url='', extra_context=None):
        filename_choices = [(filename, filename) for filename in os.listdir(settings.VM_IMAGE_DIR)]

        class AddVmForm(forms.Form):
            resource = forms.ModelChoiceField(Resource.objects.all())
            name = forms.CharField(max_length=40)
            memory = forms.IntegerField(initial=128, help_text='MiB')
            boot_type = forms.ChoiceField(choices=(('efi', 'EFI boot'), ('mbr', 'MBR boot')))
            order_id = forms.IntegerField(initial=1)
            filename = forms.ChoiceField(choices=filename_choices)

        if request.method == 'POST':
            form = AddVmForm(request.POST)
            if form.is_valid():
                image_filename = os.path.join(settings.VM_IMAGE_DIR,
                                              form.cleaned_data['filename'])
                vm_template = VMTemplate.from_image(
                    resource=form.cleaned_data['resource'],
                    name=form.cleaned_data['name'],
                    memory=form.cleaned_data['memory'],
                    boot_type=form.cleaned_data['boot_type'],
                    order_id=form.cleaned_data['order_id'],
                    image_filename=image_filename)
                messages.success(request, 'VM Template successfully added.')
                return redirect('admin:vm_vmtemplate_change', vm_template.pk)
        else:
            form = AddVmForm()

        request.current_app = self.admin_site.name
        return render(request, 'vm/add_vm_template.html', {
            'opts': self.model._meta,
            'form': form
        })


admin.site.register(VMTemplate, VMTemplateAdmin)
admin.site.register(ActiveVMResource)
admin.site.register(VirtualMachine)