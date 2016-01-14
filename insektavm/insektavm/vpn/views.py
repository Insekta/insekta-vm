import json

from django.core.exceptions import ValidationError
from django.core.validators import validate_ipv4_address
from django.http import HttpResponseBadRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db import transaction

from insektavm.base.models import UserToken
from insektavm.vpn.models import AssignedIPAddress


@require_POST
@csrf_exempt
def api_assign_ip(request):
    try:
        username = request.POST['username']
    except KeyError:
        return HttpResponseBadRequest('Parameter username is required.')

    try:
        ip_address = request.POST['ip_address']
    except KeyError:
        return HttpResponseBadRequest('Parameter ip_address is required.')

    try:
        validate_ipv4_address(ip_address)
    except ValidationError:
        return HttpResponseBadRequest('Parameter ip_address is not a valid IPv4 address.')

    user_token, created = UserToken.objects.get_or_create(username=username)
    try:
        with transaction.atomic():
            a = AssignedIPAddress.objects.select_for_update().get(user_token=user_token)
            a.ip_address = ip_address
            a.save()
    except AssignedIPAddress.DoesNotExist:
        AssignedIPAddress.objects.create(user_token=user_token, ip_address=ip_address)

    return HttpResponse(json.dumps({
        'result': 'ok'
    }), content_type='application/json')


@require_POST
@csrf_exempt
def api_unassign_ip(request):
    try:
        username = request.POST['username']
    except KeyError:
        return HttpResponseBadRequest('Parameter username is required.')

    try:
        user_token = UserToken.objects.get(username=username)
    except UserToken.DoesNotExist:
        pass
    else:
        AssignedIPAddress.objects.filter(user_token=user_token).delete()

    return HttpResponse(json.dumps({
        'result': 'ok'
    }), content_type='application/json')
