# -*- coding: utf-8 -*-
import json
import qrcode

from django.utils.six import BytesIO
from django.shortcuts import HttpResponse

from cms.handle import (WechatSdk, LoginManager, UserManager, AreaManager, StoreManager,
                        usercheck, EmployeeManager, CustomerUserManager, GoodsManager,
                        OrderManager, PeiSongManager, KuGuanManager)
from cms.apps import APIServerErrorCode as ASEC


def parse_info(data):
    """
    parser_info:
    :param data must be a dict
    :return dict data to json,and return HttpResponse
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
    # request.GET['name'],request.GET['url'])
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
    :param request:
            sign : md5 (time + Token)
            time : now time and 6s effective
    :param user:
    :return: user_type,user_info
    """

    result = {}
    body = json.loads(request.body)
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
    body = json.loads(request.body)

    action = request.GET.get('action', 'all')

    result = AreaManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def change_store_view(request, user):

    body = json.loads(request.body)

    action = request.GET.get('action', 'all')

    result = StoreManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def change_employee_view(request, user):

    body = json.loads(request.body)

    action = request.GET.get('action', 'all')

    result = EmployeeManager(action=action, postdata=body)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=1)
def change_goods_view(request, user):
    body = json.loads(request.body)

    action = request.GET.get('action', 'all')

    result = GoodsManager(action=action, postdata=body)
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

    user_store = UserManager.get_user_store(user).store
    result['message'] = 'ok'
    goods_list = StoreManager.get_store_price(user_store)

    result['goods_list'] = goods_list
    response = parse_info(result)

    return response


@usercheck(user_type=3)
def order_view(request, user):
    body = json.loads(request.body)

    action = request.GET.get('action', 'all')

    result = OrderManager(action=action, postdata=body, user=user)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=3)
def change_profile_view(request, user):
    result = {}
    body = json.loads(request.body)
    user_store = UserManager.get_user_store(user).store

    action = request.GET.get('action', 'get')

    if action == 'get':
        print(action)
        store_info = StoreManager.get_store_info(user_store)

        if 'message' in store_info:
            return store_info

        result['store_info'] = store_info
        result['message'] = 'ok'

    if action == 'set':
        this_store = UserManager.set_user_store_profile(user, body)
        result['new_store_info'] = StoreManager.get_store_info(
            this_store)
        result['message'] = 'ok'

    response = parse_info(result)

    return response


@usercheck(user_type=3)
def order_2_view(request, user, action=None, status=None):
    body = json.loads(request.body)

    if action == 'status':
        body['status'] = status

    result = OrderManager(action=action, postdata=body, user=user)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=2)
def staff_profile_view(request, action, user):
    result = {}
    body = json.loads(request.body)

    result['message'] = 'failed'

    if action == 'set':
        UserManager.set_user_peisong_profile(user=user, profile=body)
        result['message'] = 'ok'
        result['new_info'] = UserManager.get_user_peisong_profile(user=user)

    if action == 'get':
        info = UserManager.get_user_peisong_profile(user=user)
        result['message'] = 'ok'
        result['info'] = info

    response = parse_info(result)

    return response


@usercheck(user_type=2)
def staff_goods_view(request, action, user):
    result = {}

    body = json.loads(request.body)

    if action == 'all':
        result = GoodsManager.all_goods()

    response = parse_info(result)

    return response


@usercheck(user_type=2)
def staff_peisong_order_view(request, status, action, user):
    result = {}

    body = json.loads(request.body)
    peisong = PeiSongManager(user=user, postdata=body)

    # get_receive_peisong
    # set_receive_peisong
    # get_pay_peisong
    # set_pay_peisong

    try:
        method_name = action + '_' + status + '_peisong'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=2)
def staff_peisong_stock_view(request, action, user):
    result = {}

    body = json.loads(request.body)
    peisong = PeiSongManager(user=user, postdata=body)

    try:
        method_name = 'get_' + action + '_stock'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=2)
def staff_peisong_pick_view(request, action, user):
    result = {}

    body = json.loads(request.body)
    peisong = PeiSongManager(user=user, postdata=body)
    try:
        method_name = action + '_pick'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=1)
def staff_kuguan_pick_view(request, action, user):
    result = {}

    body = json.loads(request.body)
    peisong = KuGuanManager(user=user, postdata=body)
    try:
        method_name = action + '_pick'
        result = getattr(peisong, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


def test_test_view(request):

    action = request.GET.get('action', 'all')

    return HttpResponse(action)
