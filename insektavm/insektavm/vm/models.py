import hashlib

import libvirt
from django.db import models
from django.template.loader import render_to_string

from insektavm.base.virt import connections
from insektavm.base.models import UserToken
from insektavm.resources.models import Resource
from insektavm.network.models import NetworkRange, Network


CHUNK_SIZE = 8096


class VMTemplate(models.Model):
    resource = models.ForeignKey(Resource)
    name = models.CharField(max_length=40)
    memory = models.IntegerField()
    image_fingerprint = models.CharField(max_length=64)
    order_id = models.IntegerField()

    def __str__(self):
        return self.name

    def get_image_filename(self):
        return 'backing-{}.qcow2'.format(self.image_fingerprint)

    @classmethod
    def from_image(cls, resource, name, memory, order_id, image_filename):
        file_size = 0
        h = hashlib.sha256()
        with open(image_filename, 'rb') as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    break
                file_size += len(data)
                h.update(data)
        image_fingerprint = h.hexdigest()

        vm_template = cls(resource=resource,
                          name=name,
                          memory=memory,
                          image_fingerprint=image_fingerprint,
                          order_id=order_id)
        vm_template.save()
        volume_name = vm_template.get_image_filename()

        virtconn = connections['default']
        pool = virtconn.storagePoolLookupByName('insekta')
        volume_xml = render_to_string('vm/backing_volume.xml', {
            'name': volume_name,
            'capacity': file_size
        })
        try:
            volume = pool.createXML(volume_xml)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_STORAGE_VOL_EXIST:
                return vm_template
            raise
        stream = virtconn.newStream()
        volume.upload(stream, offset=0, length=file_size)
        with open(image_filename, 'rb') as f:
            while True:
                data = f.read(CHUNK_SIZE)
                if not data:
                    stream.finish()
                    break
                stream.send(data)

        return vm_template


class ActiveVMResource(models.Model):
    resource = models.ForeignKey(Resource)
    user_token = models.ForeignKey(UserToken)
    network = models.ForeignKey(Network)
    expire_time = models.DateTimeField()
    is_started = models.BooleanField(default=False)

    class Meta:
        unique_together = ('resource', 'user_token')

    def __str__(self):
        return '{} for {}'.format(self.resource, self.user_token)

    def start(self):
        if self.is_started:
            return
        network = NetworkRange.objects.get(name='default').get_free_network()
        network.libvirt_create()
        network_name = network.libvirt_get_name()
        macs = network.get_macs()
        vm_templates = VMTemplate.objects.filter(resource=self.resource).order_by('order_id')
        for vm_template, mac in zip(vm_templates, macs):
            vm = VirtualMachine(vm_resource=self,
                                template=vm_template,
                                backing_image=vm_template.image_fingerprint)
            vm.save()
            vm.libvirt_create(network_name, mac)
        self.is_started = True
        self.save()

    def stop(self):
        if not self.is_started:
            raise ValueError('VM Resource is not started yet.')
        vms = VirtualMachine.objects.filter(vm_resource=self)
        for vm in vms:
            vm.libvirt_destroy()
            vm.delete()
        self.network.free()
        self.is_started = False
        self.save()


class VirtualMachine(models.Model):
    vm_resource = models.ForeignKey(ActiveVMResource)
    template = models.ForeignKey(VMTemplate)
    backing_image = models.CharField(max_length=64)


    def __str__(self):
        return str(self.pk)

    def libvirt_create(self, network, mac):
        virtconn = connections['default']
        pool = virtconn.storagePoolLookupByName('insekta')
        backing_image_filename = self.template.get_image_filename()
        backing_vol = pool.storageVolLookupByName(backing_image_filename)
        backing_image_path = backing_vol.path()
        backing_size = backing_vol.info()[1]

        volume_xml = render_to_string('vm/volume.xml', {
            'name': self.get_volume_name(),
            'capacity': backing_size,
            'backing_image': backing_image_path
        })
        image = pool.createXML(volume_xml)
        image_filename = image.path()
        vm_tpl = self.template
        domain_xml =  render_to_string('vm/domain.xml', {
            'name': self.get_domain_name(),
            'volume': image_filename,
            'memory': vm_tpl.memory,
            'network': network,
            'mac': mac
        })
        dom = virtconn.defineXML(domain_xml)
        dom.setAutostart(1)
        dom.create()

    def libvirt_destroy(self):
        virtconn = connections['default']
        try:
            dom = virtconn.lookupByName(self.get_domain_name())
        except libvirt.libvirtError as e:
            # FIXME: Check error code
            return
        try:
            dom.destroy()
        except libvirt.libvirtError as e:
            # FIXME: Check error code
            pass
        dom.undefine()
        pool = virtconn.storagePoolLookupByName('insekta')
        try:
            vol = pool.storageVolLookupByName(self.get_volume_name())
        except libvirt.libvirtError:
            # FIXME: Check error code
            return
        vol.delete()

    def get_domain_name(self):
        return 'vm_{}'.format(self.pk)

    def get_volume_name(self):
        return 'vmimage_{}.qcow2'.format(self.pk)