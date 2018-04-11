import json
import logging

from datetime import datetime
from cms.models import Session,User
from django.http import JsonResponse
from cms.apps import APIServerErrorCode as ASEC

app = logging.getLogger('app.custom')
request_backup = logging.getLogger('app.backup')


def parse_info(data):
    """
    parser_info:
    param must be a dict
    parse dict data to json,and return HttpResponse
    """
    return JsonResponse(data)


def usercheck(user_type=-1):
    def wrapper(func):
        def inner_wrapper(*args, **kwargs):
            result = {}
            request = args[0]

            action = request.GET.get('action', None) or kwargs.get(
                'action', None) or 'None'

            try:
                body = json.loads(request.body)
                wckey = body['base_req']['wckey']
            except:
                result['code'] = ASEC.ERROR_PARAME
                result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
                response = parse_info(result)
                response.status_code = 400

                return response

            try:
                user_key = Session.objects.get(session_data=wckey)
            except Exception:
                result['code'] = ASEC.SESSION_NOT_WORK
                result['message'] = ASEC.getMessage(ASEC.SESSION_NOT_WORK)

                return parse_info(result)

            if user_key.expire_date < datetime.now():
                result['code'] = ASEC.SESSION_EXPIRED
                result['message'] = ASEC.getMessage(ASEC.SESSION_EXPIRED)

                return parse_info(result)

            user = User.objects.get(wk=user_key.session_key)

            app.info("[{}][{}][{}][{}]".format(
                func.__name__, user.wk, action, user.user_type))

            request_backup.info(str(body))

            if user_type == -1 or user.user_type <= user_type:
                return func(*args, **kwargs, user=user, body=body)
            else:
                return parse_info({'message': 'user_type failed'})

        return inner_wrapper

    return wrapper