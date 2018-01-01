# -*- coding: utf-8 -*-
import json
from django.shortcuts import render, HttpResponse

from .handle import WechatSdk, LoginManager
from .apps import APIServerErrorCode as ASEC

def parse_info(data):
    """
    parser_info:
    parmer must be in dict
    parse dict data to json,and return HttpResponse
    """
    return HttpResponse(json.dumps(data, indent=4),
                        content_type="application/json")


def index(request):
    """
    view for index:
    return status_code : 203
    no context
    """
    response = parse_info({'code': 9999})
    response.status_code = 203
    return response


def register_view(request):
    """
    view for register
    Accept the code from WeChat, and register this user on the server
    return body :{code,message}
           headers:wckey
    """
    result = {}
    if 'code' not in request.GET:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
        response = parse_info(result)
        response.status_code = 400
        return response

    wk = WechatSdk(request.GET['code'])
    if not wk.get_openid():
        result['code'] = ASEC.WRONG_PARAME
        result['message'] = ASEC.getMessage(ASEC.WRONG_PARAME)
        response = parse_info(result)
        return response

    result = wk.save_user()
    if 'sess' not in result:
        response = parse_info(result)
        return response

    sess = result.pop('sess')

    response = parse_info(result)
    response.set_cookie('wckey', sess)
    response['wckey'] = sess

    return response


def re_register_view(request):
    """
    view for re-register
    Accept the code from WeChat, and re-register this user on the server
    TODO:
        Merged with register_view interface
        

    """
    result = {}
    if 'code' not in request.GET:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
        response = parse_info(result)
        response.status_code = 400
        return response

    wk = WechatSdk(request.GET['code'])
    if not wk.get_openid():
        result['code'] = ASEC.WRONG_PARAME
        result['message'] = ASEC.getMessage(ASEC.WRONG_PARAME)
        response = parse_info(result)
        return response

    result = wk.flush_session()
    sess = result.pop('sess')

    response = parse_info(result)
    response.set_cookie('wckey', sess)
    response['wckey'] = sess

    return response


def login_view(request):
    """
    view for login

    """
    result = {}
    if 'sign' and 'time' not in request.GET:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
        response = parse_info(result)
        response.status_code = 400
        return response

    if 'wckey' not in request.COOKIES:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
        response = parse_info(result)
        response.status_code = 400
        return response

    wckey = request.COOKIES['wckey']
    user = LoginManager(wckey=wckey)

    if user.check(sign=request.GET['sign'],
                  checktime=request.GET['time']):
        result = user.reply()
        response = parse_info(result)

        return response
    else:
        result['code'] = ASEC.CHECK_USER_FAILED
        result['message'] = ASEC.getMessage(ASEC.CHECK_USER_FAILED)
        response = parse_info(result)

        return response
