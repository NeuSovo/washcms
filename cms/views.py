# -*- coding: utf-8 -*-
from django.http import JsonResponse
from django.shortcuts import HttpResponse
from cms.auth import *
from cms.handle import *
from cms.tools import gen_qrcode
from cms.apps import APIServerErrorCode as ASEC

from cms.cos import get_auth

def parse_info(data):
    """
    parser_info:
    :param data must be a dict
    :return dict data to json,and return HttpResponse
    """
    return JsonResponse(data)


def tools_sign(request):
    Method = request.GET['Method']
    Key = request.GET['Key']
    getAuth = get_auth(Method, Key, params={'Method':Method,'Key':Key})
    return HttpResponse(getAuth)


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
    img = gen_qrcode(data)
    response = HttpResponse(img, content_type="image/png")

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
    if not wk.check():
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
def login_view(request, user, body):
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
    if 'HTTP_X_FORWARDED_FOR' in request.META:
        ip = request.META['HTTP_X_FORWARDED_FOR']
    else:
        ip = request.META['REMOTE_ADDR']
    print (ip)
    result = {}
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


@usercheck()
def profile_view(request, user, body):
    t_user = UserManager.set_user_profile(user, body)
    return parse_info({'message': 'ok'})


@usercheck(user_type=0)
def change_deliveryarea_view(request, user, body):
    action = request.GET.get('action', 'all')
    result = AreaManager(action=action, postdata=body)
    
    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def change_store_view(request, user, body):
    action = request.GET.get('action', 'all')
    result = StoreManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def change_employee_view(request, user, body):
    action = request.GET.get('action', 'all')
    result = EmployeeManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=0)
def boos_report_order_view(request, user, body, action=None, day=None, month=None):
    if day is not None:
        body['day'] = day
        action = 'day'

    if month is not None:
        body['month'] = month
        action = 'month'

    report = BoosReport(user=user, postdata=body)

    try:
        method_name = action + '_order_report'
        result = getattr(report, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


@usercheck(user_type=0)
def boos_report_stock_view(request, user, body, action=None, day=None, month=None):
    if day is not None:
        body['day'] = day
        action = 'day'

    if month is not None:
        body['month'] = month
        action = 'month'

    report = BoosReport(user=user, postdata=body)

    try:
        method_name = action + '_stock_report'
        result = getattr(report, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


@usercheck(user_type=0)
def boos_report_store_view(request, user, body, day=None, month=None):
    if month is not None:
        body['month'] = month

    # down day
    action = 'month'

    report = BoosReport(user=user, postdata=body)

    try:
        method_name = action + '_store_report'
        result = getattr(report, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


@usercheck(user_type=0)
def clear_account_view(request, body, action=None, user=None):
    clear = ClearAccount(postdata=body)
    try:
        method_name = action + '_clear'
        result = getattr(clear, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


@usercheck(user_type=1)
def change_goods_view(request, user, body):
    action = request.GET.get('action', 'all')
    result = GoodsManager(action=action, postdata=body)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=4)
def bind_user_view(request, user, body):
    result = CustomerUserManager(postdata=body, user=user)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=3)
def get_user_goods_view(request, user, body):
    result = {}
    user_store = UserManager.get_user_store(user).store
    result['message'] = 'ok'
    goods_list = user_store.price()
    result['goods_list'] = goods_list

    response = parse_info(result)

    return response


@usercheck(user_type=3)
def order_view(request, user, body):
    action = request.GET.get('action', 'all')
    result = OrderManager(action=action, postdata=body, user=user)

    response = parse_info(result.reply())

    return response


@usercheck(user_type=3)
def change_profile_view(request, user, body):
    result = {}
    user_store = UserManager.get_user_store(user).store

    action = request.GET.get('action', 'get')

    if action == 'get':
        store_info = user_store.info()

        if 'message' in store_info:
            return store_info

        result['store_info'] = store_info
        result['message'] = 'ok'

    if action == 'set':
        this_store = UserManager.set_user_store_profile(user, body)
        result['new_store_info'] = this_store.info()
        result['message'] = 'ok'

    response = parse_info(result)

    return response


@usercheck(user_type=3)
def order_2_view(request, user, body, action=None, status=None):
    if action == 'status':
        body['status'] = status

    result = OrderManager(action=action, postdata=body, user=user)
    response = parse_info(result.reply())

    return response


@usercheck(user_type=3)
def recover_view(request, user, body, action=None):
    recover = RecoverManager(user=user, **body)

    try:
        method_name = action + '_recover_order'
        result = getattr(recover, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


@usercheck(user_type=3)
def user_report_view(request, user, body, month=None):
    if month is not None:
        body['month'] = month

    # down day
    action = 'month'
    report = StoreManager(user=user, postdata=body)

    try:
        method_name = action + '_store_report'
        result = getattr(report, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


@usercheck(user_type=2)
def staff_profile_view(request, action, user, body):
    result = {}
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
def staff_goods_view(request, action, user, body):
    result = {}
    if action == 'all':
        result = GoodsManager.all_goods(body.get('is_all', 0))

    response = parse_info(result)

    return response


@usercheck(user_type=2)
def staff_peisong_order_view(request, status, action, user, body):
    result = {}
    peisong = PeiSongManager(user=user, postdata=body)

    try:
        method_name = action + '_' + status + '_peisong'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=2)
def staff_peisong_stock_view(request, action, user, body):
    result = {}
    peisong = PeiSongManager(user=user, postdata=body)

    try:
        method_name = 'get_' + action + '_stock'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=2)
def staff_peisong_pick_view(request, action, user, body):
    result = {}
    peisong = PeiSongManager(user=user, postdata=body)

    try:
        method_name = action + '_pick'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=2)
def staff_peisong_report_view(request, user, body, action=None, month=None, day=None):
    result = {}
    if month is not None:
        body['month'] = month
        action = 'month'

    if day is not None:
        body['day'] = day
        action = 'day'

    peisong = PeiSongManager(user=user, postdata=body)

    try:
        method_name = action + '_order_report'
        result = getattr(peisong, method_name)
    except Exception as e:
        return parse_info({'message': str(e)})

    response = parse_info(result())

    return response


@usercheck(user_type=1)
def staff_kuguan_pick_view(request, action, user, body):
    result = {}
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


@usercheck(user_type=1)
def staff_kuguan_goods_view(request, action, user, body):
    result = {}
    goods = GoodsManager(postdata=body)

    try:
        method_name = action + '_goods'
        result = getattr(goods, method_name)
    except AttributeError as e:
        response = HttpResponse()
        response.status_code = 404
        return response

    response = parse_info(result())

    return response


def test_test_view(request):

    action = request.GET.get('action', 'all')

    return HttpResponse(action)
