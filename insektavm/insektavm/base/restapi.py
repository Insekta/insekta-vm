import functools
import json

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from insektavm.base.utils import http_basic_auth

class ApiError(Exception):
    def __init__(self, message, resp_class=HttpResponse):
        self.message = message
        self.resp_class = resp_class


def rest_api(func):
    func = csrf_exempt(func)
    func = http_basic_auth(settings.API_AUTH)(func)

    @functools.wraps(func)
    def decorator(request, *args, **kwargs):
        try:
            ret = func(request, *args, **kwargs)
            if isinstance(ret, HttpResponse):
                return ret
            elif isinstance(ret, dict):
                return HttpResponse(json.dumps(ret), content_type='application/json')
            else:
                raise ValueError('Unexpected return type for API function')
        except ApiError as e:
            return e.resp_class(e.message, content_type='text/plain')

    return decorator