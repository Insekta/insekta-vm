# Installation

This page collects the basic information needed in order to install insekta_vm. This document refers to the installation on Debian so that most likely some adaptions are necessary in order to set it up on another distribution.

Further documentation on insekta can be found on https://insekta.readthedocs.io/.

## Installation in a virtual machine

In order to install insekta_vm in a virtual machine itself, nested kvm should be enabled.
One way to achieve that is by creating a file */etc/modprobe.d/kvm-intel.conf* containing the line

| options kvm-intel nested=1

Additionally, the option *copy cpu information* needs to be enabled in the vm configuration.


## Actual installation process

### Required packages

A plain debian installation required the following packages:

* build-essential
* libvirt-bin
* libvirt-dev
* qemu-kvm
* git  (optional; zum Klonen des Codes)
* virtualenv
* python-libvirt
* python3-libvirt
* python3
* python3-dev
* python-dev
* pkg-config
* openvpn
* iptables

### Cloning the source code

Clone the source code. Install the Python requirements from the *requirements.txt* file.

### OpenVPN configuration

Copy the *openvpn* directory from *examples* to */etc/openvpn*.

Additionally, you need to uncomment the line AUTOSTART="all" in /etc/default/openvpn

```
cp -r /home/insekta/insekta-vm/insektavm/examples/openvpn/* /etc/openvpn/server/
chmod +x /etc/openvpn/server/learn-address.sh
vi /etc/openvpn/server/learn-address.sh
vi /etc/openvpn/server/server.conf
useradd --system openvpn
chown -R openvpn /etc/openvpn
systemctl enable openvpn-server@server
systemctl start openvpn-server@serve
```

### Generating CA and server key using easy-rsa

In order to sign the openvpn server certificate, a CA needs to be created. Easy-rsa can be used for that. The documentation for easy-rsa can be found in */usr/share/doc/easy-rsa*.

A CA and a certificate as well as the dh parameters need to be created.

```
make-cadir cadir
cd cadir/
vim vars
./clean-all
ln -s openssl-1.0.0.cnf openssl.cnf
./build-ca
./build-key-server server
./build-dh
```

### Copying certificates to openvpn and insekta

```
cp keys/ca.* /etc/openvpn/server/
cp keys/server.crt /etc/openvpn/server/
cp keys/server.key /etc/openvpn/server/
cp keys/dh2048.pem /etc/openvpn/server/
cp /etc/openvpn/server/ca.* /path/to/insekta-web/insekta/testenv/vpn/
```


### Setting up libvirt

The libvirt packages need to be set up on the machine.

A storage pool called *insekta* needs to be created. The vm images are placed in that pool. One way to achieve tat is by using virt-manager. It can be used on a remote host also.

If insekta is ran by a non-root user (which it should), that user needs to be added to the group libvirt.

### Setting up iptables

iptables needs to be set up in order to forward traffic from vpn to libvirt. An example configuration can be found in the examples directory. This can be placed in */etc/network/if-up.d*.

Additionally, the following command needs to be ran once:

```
sysctl -w net.ipv4.ip_forward=1
```

### Setting up Django as a daemon

To use insekta-vm as a systemd daemon you can use the example configuration found in *insekta-vm/insektavm/examples/systemd*.


