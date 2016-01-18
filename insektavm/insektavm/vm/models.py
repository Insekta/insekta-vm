from datetime import timedelta
import hashlib

import libvirt
from django.db import models, transaction
from django.template.loader import render_to_string
from django.utils.timezone import now

from insektavm.base.virt import connections
from insektavm.base.models import UserToken
from insektavm.resources.models import Resource
from insektavm.network.models import NetworkRange, Network
from insektavm.vpn.models import AssignedIPAddress
from insektavm.vpn.signals import ip_assigned, ip_unassigned

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
        # Make sure just one process is starting this VM
        if self.pk:
            with transaction.atomic():
                vm_res = ActiveVMResource.objects.select_for_update().get(pk=self.pk)
                # Some other process was faster
                if vm_res.is_started:
                    return
                vm_res.is_started = True
                vm_res._ping()
                vm_res.save()

        self._ping()
        self.is_started = True

        self.network = NetworkRange.objects.get(name='default').get_free_network()

        # We save it now because:
        # 1) we don't want to loose information if something with libvirt fails
        # 2) we want to make sure the object is in the database so others can relate to it.
        self.save()

        self.network.libvirt_create()
        macs = self.network.get_macs()
        vm_templates = VMTemplate.objects.filter(resource=self.resource).order_by('order_id')
        for vm_template, mac in zip(vm_templates, macs):
            vm = VirtualMachine(vm_resource=self,
                                template=vm_template,
                                backing_image=vm_template.image_fingerprint)
            vm.save()
            vm.libvirt_create(self.network, mac)

        try:
            ip = AssignedIPAddress.objects.get(user_token=self.user_token).ip_address
            self.network.grant_access(ip)
        except AssignedIPAddress.DoesNotExist:
            pass

    def stop(self):
        self._stop()
        self.is_started = False
        self.save()

    def destroy(self):
        self._stop()
        self.delete()

    def ping(self):
        self._ping()
        self.save()
        return self.expire_time

    def _stop(self):
        if not self.is_started:
            raise ValueError('VM Resource is not started yet.')
        vms = VirtualMachine.objects.filter(vm_resource=self)
        for vm in vms:
            vm.libvirt_destroy()
            vm.delete()
        self.network.revoke_access()
        self.network.free()

    def _ping(self):
        self.expire_time = now() + timedelta(minutes=30)

    def get_vms(self):
        vm_objs = (VirtualMachine.objects.filter(vm_resource=self)
                   .select_related('template')
                   .order_by('template__order_id'))
        vms = []
        for vm_obj, ip in zip(vm_objs, self.network.get_vm_ips()):
            vms.append({
                'name': vm_obj.template.name,
                'ip': str(ip)
            })
        return vms

    @classmethod
    def start_for(cls, resource, user_token):
        try:
            vm_res = cls.objects.get(resource=resource, user_token=user_token)
        except cls.DoesNotExist:
            vm_res = cls(resource=resource, user_token=user_token)
        vm_res.start()
        return vm_res


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
        network_name = network.libvirt_get_name()
        nwfilter_name = network.libvirt_get_nwfilter_name()
        domain_xml =  render_to_string('vm/domain.xml', {
            'name': self.get_domain_name(),
            'volume': image_filename,
            'memory': vm_tpl.memory,
            'network': network_name,
            'mac': mac,
            'nwfilter_name': nwfilter_name
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


def _callback_ip_assigned(sender, user_token, ip_address, **kwargs):
    for vm_res in ActiveVMResource.objects.filter(user_token=user_token, is_started=True):
        vm_res.network.grant_access(ip_address)


def _callback_ip_unassigned(sender, user_token, **kwargs):
    for vm_res in ActiveVMResource.objects.filter(user_token=user_token, is_started=True):
        vm_res.network.revoke_access()


ip_assigned.connect(_callback_ip_assigned)
ip_unassigned.connect(_callback_ip_unassigned)
