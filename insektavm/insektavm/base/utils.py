import base64
import functools

from django.http import HttpResponse
from django.utils.crypto import constant_time_compare


def http_basic_auth(auth, realm='Restricted area'):
    def http_basic_auth(func):
        @functools.wraps(func)
        def _decorator(request, *args, **kwargs):
            if 'HTTP_AUTHORIZATION' in request.META:
                method, basic_auth = request.META['HTTP_AUTHORIZATION'].split(' ', 1)
                if method.lower() == 'basic':
                    try:
                        basic_auth = base64.b64decode(basic_auth.strip()).decode('utf-8')
                        username, password = basic_auth.split(':', 1)
                    except (ValueError, UnicodeDecodeError):
                        pass
                    else:
                        expected_username, expected_password = auth
                        has_access = (constant_time_compare(username, expected_username) and
                                      constant_time_compare(password, expected_password))
                        if has_access:
                            return func(request, *args, **kwargs)
            resp = HttpResponse('Unauthorized',
                                status=401,
                                reason='Unauthorized',
                                content_type='text/plain')
            resp['WWW-Authenticate'] = 'Basic realm="{}"'.format(realm)
            return resp
        return _decorator

    return http_basic_auth
