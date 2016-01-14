import calendar
import json

from django.http import HttpResponseBadRequest, HttpResponseNotFound, HttpResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from insektavm.base.models import UserToken
from insektavm.resources.models import Resource
from insektavm.vm.models import ActiveVMResource


@require_POST
@csrf_exempt
def api_start_vm(request):
    resource, user_token = _api_get_parameters(request)
    vm_res = ActiveVMResource.start_for(resource, user_token)
    return HttpResponse(json.dumps({
        'id': vm_res.pk,
        'expire': calendar.timegm(vm_res.expire_time.utctimetuple()),
        'virtual_machines': vm_res.get_vms()
    }), content_type='application/json')


@require_POST
@csrf_exempt
def api_stop_vm(request):
    resource, user_token = _api_get_parameters(request)
    try:
        vm_res = ActiveVMResource.objects.get(resource=resource, user_token=user_token)
    except ActiveVMResource.DoesNotExist:
        return HttpResponseNotFound('No such network is running')
    vm_res.destroy()
    return HttpResponse(json.dumps({
        'result': 'ok'
    }), content_type='application/json')


@require_POST
@csrf_exempt
def api_ping_vm(request):
    resource, user_token = _api_get_parameters(request)
    try:
        vm_res = ActiveVMResource.objects.get(resource=resource, user_token=user_token)
    except ActiveVMResource.DoesNotExist:
        return HttpResponseNotFound('No such network is running')
    expire_time = vm_res.ping()
    return HttpResponse(json.dumps({
        'id': vm_res.pk,
        'expire': calendar.timegm(expire_time.utctimetuple())
    }), content_type='application/json')


def _api_get_parameters(request):
    try:
        resource_str = request.POST['resource']
    except KeyError:
        return HttpResponseBadRequest('Require resource parameter.')
    try:
        username = request.POST['username']
    except KeyError:
        return HttpResponseBadRequest('Require username parameter')

    try:
        resource = Resource.objects.get(name=resource_str, type='vmnet')
    except Resource.DoesNotExist:
        return HttpResponseNotFound('No such resource: {}'.format(resource_str))

    user_token, created = UserToken.objects.get_or_create(username=username)

    return resource, user_token