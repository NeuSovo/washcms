# -*- coding: utf-8 -*-
import json
from django.shortcuts import render, HttpResponse

from .handle import WechatSdk, LoginManager
from .apps import APIServerErrorCode as ASEC

def parse_info(data):
    return HttpResponse(json.dumps(data, indent=4),
                        content_type="application/json")


def register_view(request):
    result = {}

    if 'code' not in request.GET:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)          # 参数错误
        response = parse_info(result)
        return response

    wk = WechatSdk(request.GET['code'])
    if not wk.get_openid():
        result['code'] = ASEC.WRONG_PARAME
        result['message'] = ASEC.getMessage(ASEC.WRONG_PARAME)         # 参数错误
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
    result = {}
    if 'code' not in request.GET:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)           # 参数错误
        response = parse_info(result)
        return response

    wk = WechatSdk(request.GET['code'])
    if not wk.get_openid():
        result['code'] = ASEC.WRONG_PARAME
        result['message'] = ASEC.getMessage(ASEC.WRONG_PARAME)          # 参数错误
        response = parse_info(result)
        return response

    result = wk.flush_session()
    sess = result.pop('sess')

    response = parse_info(result)
    response.set_cookie('wckey', sess)
    response['wckey'] = sess

    return response


def login_view(request):
    result = {}
    if 'sign' and 'time' not in request.GET:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)         # 参数错误
        response = parse_info(result)
        return response

    if 'wckey' not in request.COOKIES:
        result['code'] = ASEC.ERROR_PARAME
        result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)         # 参数错误
        response = parse_info(result)
        return response

    wckey = request.COOKIES['wckey']
    user = LoginManager(wckey=wckey)

    if user.check(sign=request.GET['sign'],
                  checktime=request.GET['time']):
        result = user.reply()
        response = parse_info(result)

        return response
    else:
        result['code'] = ASEC.WRONG_PARAME
        result['message'] = ASEC.getMessage(ASEC.WRONG_PARAME)       # 参数错误
        response = parse_info(result)
        
        return response
