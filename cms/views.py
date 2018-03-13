# -*- coding: utf-8 -*-
import json
import qrcode

from django.utils.six import BytesIO
from django.shortcuts import HttpResponse

from cms.handle import (WechatSdk, LoginManager, UserManager, AreaManager, StoreManager, 
                        usercheck,EmployeeManager,CustomerUserManager,GoodsManager,
                        OrderManager)
from cms.apps import APIServerErrorCode as ASEC


def parse_info(data):
    """
    parser_info:
    :param data must be a dict
    :parse dict data to json,and return HttpResponse
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


def qrcode_view(request, data):
    img = qrcode.make(data)

    buf = BytesIO()
    img.save(buf)
    image_stream = buf.getvalue()
 
    response = HttpResponse(image_stream, content_type="image/png")

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

    # update 2018/03/07
    wk = WechatSdk(request.GET['code'])  # request.GET['name'],request.GET['url'])
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
def login_view(request, user):
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

    # wckey = body['base_req']['wckey']
    login = LoginManager(user=user)
    if login.check(sign=body['sign'],
                   checktime=body['time']):
        result = login.reply()
        response = parse_info(result)

        return response
    else:
        result['code'] = ASEC.CHECK_USER_FAILED
        result['message'] = ASEC.getMessage(ASEC.CHECK_USER_FAILED)
        response = parse_info(result)

        return response


@usercheck(user_type=0)
def change_deliveryarea_view(request, user):
    """
        add
        del
        change
        {
        'base_req':{
            'wckey':'',
            }
        }
    """
    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = 'all'
    else:
        action = request.GET['action']

    result = AreaManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def change_store_view(request, user):

    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = 'all'
    else:
        action = request.GET['action']

    result = StoreManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def change_employee_view(request, user):

    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = 'all'
    else:
        action = request.GET['action']

    result = EmployeeManager(action=action, postdata=body)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=1)
def change_goods_view(request, user):
    """
    """
    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = 'all'
    else:
        action = request.GET['action']

    result = GoodsManager(action=action,postdata=body)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=4)
def bind_user_view(request, user):
    body = json.loads(request.body)

    result = CustomerUserManager(postdata=body, user=user)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=3)
def get_user_goods_view(request, user):
    result = {}

    body = json.loads(request.body)

    user_store_id = UserManager.get_user_store_id(user)
    result['message'] = 'ok'
    goods_list = StoreManager.get_store_price(user_store_id)
    
    for i,item in enumerate(goods_list):
        goods_info = GoodsManager.get_goods_info(item['goods_id'])
        goods_stock = goods_info['goods_stock']
        is_recover = goods_info['is_recover']
        goods_list[i]['goods_stock'] = goods_stock
        goods_list[i]['is_revoer'] = is_recover
    
    result['goods_list'] = goods_list
    response = parse_info(result)

    return response


@usercheck(user_type=3)
def order_view(request, user):
    body = json.loads(request.body)

    if 'action' not in request.GET:
        action = ''
    else:
        action = request.GET['action']

    result = OrderManager(action=action, postdata=body, user=user)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=3)
def change_profile_view(request, user):
    result = {}
    body = json.loads(request.body)
    user_store_id = UserManager.get_user_store_id(user)

    if 'action' not in request.GET:
        action = 'get'
    else :
        action = request.GET['action']

    if action is 'get':
        store_info = StoreManager.get_store_info(user_store_id)
        
        if 'message' in store_info:
            return store_info

        result['store_info'] = store_info
        result['message'] = 'ok'

    if action == 'set':
        this_store = UserManager.set_user_store_profile(user, body)
        result['new_store_info'] = StoreManager.get_store_info(this_store.store_id)
        result['message'] = 'ok'

    response = parse_info(result)

    return response


@usercheck(user_type=3)
def test_view(request,user,action,status = None):
    body = json.loads(request.body)

    if action == 'status':
        body['status'] = status

    result = OrderManager(action=action,postdata=body, user=user)