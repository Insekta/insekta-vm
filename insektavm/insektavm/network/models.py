import hashlib
import ipaddress
import subprocess
import os

import libvirt
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models.signals import post_save
from django.template.loader import render_to_string

from insektavm.base.virt import connections


SCRIPT_DIR = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'scripts')


class IPv4NetworkField(models.Field):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        try:
            return ipaddress.IPv4Network(value)
        except ipaddress.AddressValueError as e:
            raise ValidationError(str(e))

    def get_prep_value(self, value):
        return str(value)

    def to_python(self, value):
        if isinstance(value, ipaddress.IPv4Network) or value is None:
            return value
        try:
            return ipaddress.IPv4Network(value)
        except ipaddress.AddressValueError as e:
            raise ValidationError(str(e))

    def db_type(self, connection):
        return 'varchar(18)'


class NetworkRange(models.Model):
    name = models.CharField(max_length=40, unique=True)
    network = IPv4NetworkField()
    subnet_prefix = models.IntegerField()

    @transaction.atomic
    def create_subnets(self):
        for subnet in self.network.subnets(new_prefix=self.subnet_prefix):
            Network.objects.create(network=subnet, range=self)

    @staticmethod
    def post_save(sender, instance, created, **kwargs):
        if created:
            instance.create_subnets()

    @transaction.atomic
    def get_free_network(self):
        # FIXME: Check if there are free networks
        network = Network.objects.select_for_update().filter(in_use=False)[:1][0]
        network.in_use = True
        network.save()
        return network

    def __str__(self):
        return '{}: {}'.format(self.name, self.network)


class Network(models.Model):
    network = IPv4NetworkField()
    range = models.ForeignKey(NetworkRange, related_name='subnet', on_delete=models.CASCADE)
    in_use = models.BooleanField(default=False)

    def __str__(self):
        return str(self.network)

    def libvirt_get_name(self):
        return 'insekta_vmnet_{}'.format(self.pk)

    def libvirt_create(self):
        virtconn = connections['default']
        network_name = self.libvirt_get_name()
        try:
            return virtconn.networkLookupByName(network_name)
        except libvirt.libvirtError as e:
            if e.get_error_code() != libvirt.VIR_ERR_NO_NETWORK:
                raise
        hosts = self.network.hosts()
        network_gateway = next(hosts)
        host_list = list(hosts)
        first_host = host_list[0]
        # Last host is reserved for the user, we don't want it to be taken by a vm
        last_host = host_list.pop()
        vm_hosts = []
        for i, (host, mac) in enumerate(zip(host_list, self.get_macs())):
            vm_hosts.append({
                'addr': host,
                'mac': mac,
                'name': 'vm{}'.format(str(i).zfill(2))
            })
        network_xml = render_to_string('network/network.xml', {
            'name': self.libvirt_get_name(),
            'hosts': vm_hosts,
            'network_address': str(self.network.network_address),
            'network_mask': str(self.network.netmask),
            'network_gateway': str(network_gateway),
            'dhcp_range_start': first_host,
            'dhcp_range_end': last_host
        })
        net = virtconn.networkDefineXML(network_xml)
        net.setAutostart(True)
        net.create()
        self.libvirt_create_nwfilter()
        return net

    def libvirt_destroy(self):
        virtconn = connections['default']
        network_name = self.libvirt_get_name()
        try:
            net = virtconn.networkLookupByName(network_name)
        except libvirt.libvirtError as e:
            if e.get_error_code() == libvirt.VIR_ERR_NO_NETWORK:
                raise
            return

        try:
            net.destroy()
        except libvirt.libvirtError:
            pass
        try:
            net.undefine()
        except libvirt.libvirtError:
            pass
        self.libvirt_destroy_nwfilter()

    def libvirt_get_nwfilter_name(self):
        return 'vmnetnwfilter_{}'.format(self.pk)

    def libvirt_create_nwfilter(self, ip_address=None):
        name = self.libvirt_get_nwfilter_name()
        h = hashlib.sha256(name.encode()).hexdigest()
        uuid = '{}-{}-{}-{}-{}'.format(h[0:8], h[8:12], h[12:16], h[16:20], h[20:32])
        nwfilter_xml = render_to_string('network/nwfilter.xml', {
            'name': name,
            'uuid': uuid,
            'ip_address': ip_address,
            'network_address': str(self.network.network_address),
            'network_mask': str(self.network.netmask),
        })
        virtconn = connections['default']
        return virtconn.nwfilterDefineXML(nwfilter_xml)

    def libvirt_destroy_nwfilter(self):
        virtconn = connections['default']
        try:
            f = virtconn.nwfilterLookupByName(self.libvirt_get_nwfilter_name())
        except libvirt.libvirtError:
            pass
        else:
            f.undefine()

    def get_macs(self):
        if self.network.num_addresses > 256:
            raise ValueError('Too large network to create MACs. Largest is /24.')
        if self.pk >= (1 << 16):
            raise ValueError('Network has a too large primary key. Max is 16 bit.')
        assert self.pk < (1 << 16)
        kvm_prefix = '54:52:00'
        pk_higher = self.pk >> 8
        pk_lower = self.pk & 0xff
        return ['{}:{:0>2x}:{:0>2x}:{:0>2x}'.format(kvm_prefix, pk_higher, pk_lower, i)
                for i in range(self.network.num_addresses)]

    def get_vm_ips(self):
        # First host is the gateway, last host might be a user
        return list(self.network.hosts())[1:-1]

    def free(self):
        self.in_use = False
        self.libvirt_destroy()
        self.save()

    def grant_access(self, ip_address):
        self.libvirt_create_nwfilter(str(ip_address))

    def revoke_access(self):
        self.libvirt_create_nwfilter()


post_save.connect(NetworkRange.post_save, sender=NetworkRange)
