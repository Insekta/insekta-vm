from django.core.signals import Signal

ip_assigned = Signal()
ip_unassigned = Signal()

VPNSender = object()
