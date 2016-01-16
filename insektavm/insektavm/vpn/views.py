from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address
from django.http import HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.db import transaction

from insektavm.base.models import UserToken
from insektavm.base.restapi import ApiError, rest_api
from insektavm.vpn.models import AssignedIPAddress
from insektavm.vpn.signals import VPNSender, ip_assigned, ip_unassigned


@require_POST
@rest_api
def api_assign_ip(request):
    try:
        username = request.POST['username']
    except KeyError:
        raise ApiError('Parameter username is required.', HttpResponseBadRequest)

    try:
        ip_address = request.POST['ip_address']
    except KeyError:
        raise ApiError('Parameter ip_address is required.', HttpResponseBadRequest)

    try:
        validate_ipv4_address(ip_address)
    except ValidationError:
        raise ApiError('Parameter ip_address is not a valid IPv4 address.',
                       HttpResponseBadRequest)

    user_token, created = UserToken.objects.get_or_create(username=username)

    # Try to unassign the IP address first if it belongs to another user,
    # in case we lost some notification
    _unassign_ip(ip_address)

    # Now save the user -> ip mapping or update it
    try:
        with transaction.atomic():
            a = AssignedIPAddress.objects.select_for_update().get(user_token=user_token)
            a.ip_address = ip_address
            a.save()
    except AssignedIPAddress.DoesNotExist:
        AssignedIPAddress.objects.create(user_token=user_token, ip_address=ip_address)

    ip_assigned.send_robust(VPNSender, user_token=user_token, ip_address=ip_address)

    return {
        'result': 'ok'
    }


@require_POST
@rest_api
def api_unassign_ip(request):
    # Unassign via user
    try:
        username = request.POST['username']
        user_token = UserToken.objects.get(username=username)
    except (KeyError, UserToken.DoesNotExist):
        pass
    else:
        AssignedIPAddress.objects.filter(user_token=user_token).delete()
        ip_unassigned.send_robust(VPNSender, user_token=user_token)

    # Unassign via IP
    try:
        ip_address = request.POST['ip_address']
        validate_ipv4_address(ip_address)
    except ValidationError:
        raise ApiError('Parameter ip_address is not a valid IPv4 address.',
                       HttpResponseBadRequest)
    except KeyError:
        pass
    else:
        _unassign_ip(ip_address)

    return {
        'result': 'ok'
    }


def _unassign_ip(ip_address):
    try:
        a = AssignedIPAddress.objects.select_related().get(ip_address=ip_address)
        a.delete()
        ip_unassigned.send_robust(VPNSender, user_token=a.user_token)
    except AssignedIPAddress.DoesNotExist:
        pass
