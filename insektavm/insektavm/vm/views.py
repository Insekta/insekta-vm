import calendar

from django.http import HttpResponseBadRequest, HttpResponseNotFound
from django.views.decorators.http import require_POST, require_GET

from insektavm.base.models import UserToken
from insektavm.base.restapi import ApiError, rest_api
from insektavm.resources.models import Resource
from insektavm.vm.models import ActiveVMResource


@require_POST
@rest_api
def api_start_vm(request):
    resource, user_token = _api_get_parameters(request.POST)
    vm_res = ActiveVMResource.start_for(resource, user_token)
    return _vm_res_json(vm_res)


@require_POST
@rest_api
def api_stop_vm(request):
    resource, user_token = _api_get_parameters(request.POST)
    try:
        vm_res = ActiveVMResource.objects.get(resource=resource, user_token=user_token)
    except ActiveVMResource.DoesNotExist:
        raise ApiError('No such network is running', HttpResponseNotFound)
    vm_res.destroy()
    return {
        'result': 'ok'
    }


@require_POST
@rest_api
def api_ping_vm(request):
    resource, user_token = _api_get_parameters(request.POST)
    try:
        vm_res = ActiveVMResource.objects.get(resource=resource, user_token=user_token)
    except ActiveVMResource.DoesNotExist:
        raise ApiError('No such network is running', HttpResponseNotFound)
    expire_time = vm_res.ping()
    return {
        'id': vm_res.pk,
        'expire': _to_timestamp(expire_time)
    }


@require_GET
@rest_api
def api_get_vm_status(request):
    resource, user_token = _api_get_parameters(request.GET)
    try:
        vm_res = ActiveVMResource.objects.get(resource=resource, user_token=user_token)
        status = 'running'
        resource = _vm_res_json(vm_res)
    except ActiveVMResource.DoesNotExist:
        status = 'notrunning'
        resource = None
    return {
        'status': status,
        'resource': resource
    }


def _api_get_parameters(params):
    try:
        resource_str = params['resource']
    except KeyError:
        raise ApiError('Require resource parameter.', HttpResponseBadRequest)
    try:
        username = params['username']
    except KeyError:
        raise ApiError('Require username parameter.', HttpResponseBadRequest)

    try:
        resource = Resource.objects.get(name=resource_str, type='vmnet')
    except Resource.DoesNotExist:
        raise ApiError('No such resource: {}'.format(resource_str), HttpResponseNotFound)

    user_token, created = UserToken.objects.get_or_create(username=username)

    return resource, user_token


def _vm_res_json(vm_res):
    return {
        'id': vm_res.pk,
        'expire': _to_timestamp(vm_res.expire_time),
        'virtual_machines': vm_res.get_vms()
    }


def _to_timestamp(expire_time):
    return calendar.timegm(expire_time.utctimetuple())
