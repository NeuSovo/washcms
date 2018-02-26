# -*- coding: utf-8 -*-
import json
from django.shortcuts import HttpResponse

from cms.handle import (WechatSdk, LoginManager, AreaManager, StoreManager, 
                        usercheck,SetUserManager,BindUserManager)
from cms.apps import APIServerErrorCode as ASEC


def parse_info(data):
    """
    parser_info:
    parmer must be a dict
    parse dict data to json,and return HttpResponse
    """
    return HttpResponse(json.dumps(data, indent=4),
                        content_type="application/json")


def index(request):
    """
    view for index:
    return status_code : 203
    no content
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

    sess = result['sess']

    response = parse_info(result)
    response.set_cookie('wckey', sess)
    # response['wckey'] = sess

    return response


'''
def re_register_view(request):
    """
    view for re-register
    Accept the code from WeChat, and re-register this user on the server
    
    ***Merged with register_view interface***
'''

@usercheck()
def login_view(request):
    """
    view for login
    Accept User Cookies and return user info,
    This interface must Verify sign.
    Request parmes :
        sign : md5 (time + Token)
        time : nowtime and 30s effective
    Request Headers:
        cookies : wckey
    Return 
        user_type
        user_info
    """
    result = {}
    body = json.loads(request.body)

    wckey = body['base_req']['wckey']
    user = LoginManager(wckey=wckey)
    if user.check(sign=body['sign'],
                  checktime=body['time']):
        result = user.reply()
        response = parse_info(result)

        return response
    else:
        result['code'] = ASEC.CHECK_USER_FAILED
        result['message'] = ASEC.getMessage(ASEC.CHECK_USER_FAILED)
        response = parse_info(result)

        return response


@usercheck(user_type = 0)
def change_deliveryarea_view(request):
    '''
        add
        del
        change
        {
        'base_req':{
            'wckey':'',
            }
        }
    '''
    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = 'all'
    else:
        action = request.GET['action']

    result = AreaManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type = 0)
def change_storeinfo_view(request):

    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = 'all'
    else:
        action = request.GET['action']

    result = StoreManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type = 0)
def set_user_type_view(request):
    '''
    Admin 0
    peisong 1
    kuguan 2
    '''
    body = json.loads(request.body)

    result = SetUserManager(postdata = body)
    response = parse_info(result.reply())

    return response


@usercheck(user_type = 4)
def bind_user_view(request):
    body = json.loads(request.body)

    result = BindUserManager(postdata = body)
    response = parse_info(result.reply())

    return response