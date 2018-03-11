# -*- coding: utf-8 -*-
import os
import json
import time
import base64
import random
import logging
import requests
from hashlib import sha256, md5

from django.db.models import Q
from django.conf import settings
from django.shortcuts import HttpResponse

from datetime import datetime, timedelta

from cms.models import *
from cms.apps import APIServerErrorCode as ASEC

# from cms.views import *

app = logging.getLogger('app.custom')


def parse_info(data):
    """
    parser_info:
    param must be a dict
    parse dict data to json,and return HttpResponse
    """
    return HttpResponse(json.dumps(data, indent=4),
                        content_type="application/json")


def get_user(wckey):
    user_key = Session.objects.get(session_data=wckey)
    user = User.objects.get(wk=user_key.session_key)

    return user


def usercheck(user_type=-1):
    def wrapper(func):
        def inner_wrapper(request):
            result = {}
            try:
                print(request.body)
                body = json.loads(request.body)
                wckey = body['base_req']['wckey']
                if 'action' in request.GET:
                    app.info("[backup data] {}\t{}:{}".format(
                        func.__name__, request.GET['action'], body))

                app.info("[backup data] {}:{}".format(func.__name__, body))
            except Exception as e:
                app.info(str(e))
                result['code'] = ASEC.ERROR_PARAME
                result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
                response = parse_info(result)
                response.status_code = 400

                return response

            try:
                user_key = Session.objects.get(session_data=wckey)
            except Exception as e:
                app.error(str(e) + 'wckey:{}'.format(wckey))
                result['code'] = ASEC.SESSION_NOT_WORK
                result['message'] = ASEC.getMessage(ASEC.SESSION_NOT_WORK)

                return parse_info(result)

            if user_key.expire_date < datetime.now():
                result['code'] = ASEC.SESSION_EXPIRED
                result['message'] = ASEC.getMessage(ASEC.SESSION_EXPIRED)

                return parse_info(result)

            user = UserManager.get_user(wckey=wckey)

            if user_type == -1 or user.user_type <= user_type:
                return func(request, user)
            else:
                return parse_info({'message': 'user_type failed'})

        return inner_wrapper

    return wrapper


class WechatSdk(object):
    __Appid = 'wx5c7d55175f3872b7'
    __SECRET = '6050b3ca9c9b3823768ae1867ef9036e'
    """
    WechatSdk
    Based on Wechat user code
    """
    openid = ''
    wxsskey = ''

    def __init__(self, code):
        super(WechatSdk, self).__init__()
        self.code = code

    @staticmethod
    def gen_hash():
        """
        gen_hash as session data.
        The repetition should be a very small probability event,
        and from a statistical point of view, the probability is zero.
        Return a string of length 64.
        """
        return sha256(os.urandom(24)).hexdigest()

    def get_openid(self):
        params = {
            'appid': self.__Appid,
            'secret': self.__SECRET,
            'js_code': self.code,
            'grant_type': 'authorization_code'
        }

        try:
            data = requests.get(
                'https://api.weixin.qq.com/sns/jscode2session', params=params)
        except Exception as e:
            app.error(str(e) + '\tcode:' + str(self.code))
            return False

        info = data.json()
        # print(info)
        if 'openid' not in info:
            app.info('parameter \'{}\' error'.format(self.code))
            if settings.DEBUG:
                info = {
                    'openid': self.code,
                    'session_key': 'SESSIONKEY',
                }
            else:
                return False

        self.openid = info['openid']
        self.wxsskey = info['session_key']

        app.info(self.code + ':\t' + self.openid)

        return True

    def save_user(self):
        have_user = User.objects.filter(wk=self.openid)
        if len(have_user) != 0:
            # 已注册过
            return self.flush_session()

        sess = WechatSdk.gen_hash()

        Session(session_key=self.openid,
                session_data=sess,
                we_ss_key=self.wxsskey,
                expire_date=datetime.now() + timedelta(30)).save()

        user = User(wk=self.openid)
        user.save()
        # 自动为用户生成Profile
        # Profile(wk=user).save()

        # 注册成功，分配cookie
        return {'sess': sess,
                'code': ASEC.REG_SUCCESS,
                'message': ASEC.getMessage(ASEC.REG_SUCCESS)}

    def flush_session(self):
        this_user = Session.objects.get(session_key=self.openid)
        sess = WechatSdk.gen_hash()

        this_user.we_ss_key = self.wxsskey
        this_user.session_data = sess
        this_user.expire_date = datetime.now() + timedelta(30)
        this_user.save()

        # 刷新Cookie成功
        return {'sess': sess,
                'code': ASEC.FLUSH_SESSION_SUCCESS,
                'message': ASEC.getMessage(ASEC.FLUSH_SESSION_SUCCESS)}


class LoginManager(object):
    TOKEN = 'eq021n!3'

    def __init__(self, user):
        super(LoginManager, self).__init__()
        self.user = user

    def __str__(self):
        return self.user

    def check(self, sign, checktime):
        if time.time() - int(checktime) > 30:
            return False

        to_check_str = str(self.TOKEN) + str(checktime)
        to_check_str = to_check_str.encode('utf-8')

        m = md5()
        m.update(to_check_str)

        cc_str = m.hexdigest()
        del m
        if settings.DEBUG:
            return True
        else:
            return cc_str == sign

    @staticmethod
    def gen_base64(txt):
        tmp = base64.b64encode(str(txt).encode('utf-8'))
        return str(tmp, 'utf-8')

    def reply(self):
        user = self.user
        user.last_login = datetime.now()
        user_info = UserManager.get_user_info(user)

        if settings.DEBUG:
            user_info['qrcode'] = 'https://wash.wakefulness.cn/tools/qrcode/' + \
                user_info['qrcode']
        user.save()

        return {'code': ASEC.LOGIN_SUCCESS,
                'user_type': user.user_type,
                'info': user_info,
                'message': ASEC.getMessage(ASEC.LOGIN_SUCCESS)}


class UserManager(object):

    @staticmethod
    def get_user(wckey=None):
        """
        :param wckey:
        :return: user
        """
        if None:
            return None

        user_key = Session.objects.get(session_data=wckey)
        user = User.objects.get(wk=user_key.session_key)

        return user

    @staticmethod
    def get_user_info(user):
        """
        :param user:
        :return: name,avatar_links
                and base64(user.wk)
        """
        name = user.nick_name
        avatar_links = user.avatar_links

        return {'name': name,
                'avatar_links': avatar_links,
                'user_type': user.user_type,
                'qrcode': LoginManager.gen_base64(user.wk)}

    @staticmethod
    def get_user_store_id(user):
        """
        User_type must be 3
        :param user:
        :return: Customer User store id
        """
        return CustomerProfile.objects.get(wk=user).store_id

    @staticmethod
    def get_user_area_id(user):
        """
        User_type must be 2
        :param user:
        :return: Courier User Area id
        """
        return CourierProfile.objects.get(wk=user).area_id

    @staticmethod
    def set_user_profile(user, profile):
        """
        :param user:
        :param profile:
        :return:
        """
        user.nick_name = profile['name']
        user.avatar_links = profile['url']
        user.save()

        return user

    @staticmethod
    def set_user_store_profile(user, profile):
        """
        only user type is 3
        """
        store_id = UserManager.get_user_store_id(user)
        store = Store.objects.get(store_id=store_id)

        store.store_addr = profile['addr']
        store.store_phone = profile['phone']
        store.store_name = profile['name']
        store.save()

        return store

    @staticmethod
    def set_user_type(user, set_type, area_id=-1):
        """
        set_type = 0,1,2
        """
        if set_type == 2:
            CourierProfile(wk=user, area_id=area_id).save()

        user.user_type = set_type
        user.save()

        return user


class AreaManager(object):
    def __init__(self, action, postdata):
        self.action = action
        self.data = postdata

    @staticmethod
    def check_area_id_exist(area_id):
        try:
            DeliveryArea.objects.get(id=area_id)
            return True
        except Exception as e:
            app.error(str(e))
            return False

    def add_area(self):
        new_area = DeliveryArea(area_name=self.data['name'])
        new_area.save()

        return {'message': 'ok', 'id': new_area.id}

    def del_area(self):
        try:
            to_delete = DeliveryArea.objects.get(id=self.data['id'])
            if len(CourierProfile.objects.filter(area_id=self.data['id'])) != 0:
                return {'message': '请确保此区域下已没有配送员'}
            if len(Store.objects.filter(store_area=self.data['id'])) != 0:
                return {'message': '请确保此区域下已没有商家'}

            to_delete.delete()
        except Exception as e:
            app.info(str(e))
            return {'message': '删除失败,可能成功'}

        return {'message': 'ok'}

    def change_area(self):
        area = DeliveryArea.objects.get(id=self.data['id'])
        area.area_name = self.data['name']
        area.save()
        return {'message': 'ok', 'new_name': area.area_name}

    @staticmethod
    def all_area():
        all_area = DeliveryArea.area_all()
        all_area_list = []

        for _i in all_area:
            all_area_list.append({'id': _i.id,
                                  'name': _i.area_name})

        return {'message': 'ok',
                'info': all_area_list}

    @staticmethod
    def get_area_name(area_id=-1):
        return DeliveryArea.objects.get(id=area_id).area_name

    def reply(self):
        method_name = self.action + '_area'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.info(str(e))
            return AreaManager.all_area()


class StoreManager(object):
    """docstring for StoreManager"""

    def __init__(self, action, postdata):
        self.action = action
        self.data = postdata

    @staticmethod
    def check_id_exist(store_id):
        try:
            Store.objects.get(store_id=store_id)
            return True
        except:
            return False

    @staticmethod
    def gen_store_id():
        while True:
            store_id = random.randint(10000, 99999)
            if not StoreManager.check_id_exist(store_id):
                return store_id

    def add_store(self):
        data = self.data
        store_id = StoreManager.gen_store_id()
        new_store = Store(store_id=store_id,
                          store_name=data['name'],
                          # store_phone=data['phone'],
                          # store_addr=data['addr'],
                          store_area=data['area'],
                          store_pay_type=data['pay_type'],
                          store_deposit=data['deposit'])

        new_store.save()

        return {'message': 'ok', 'id': new_store.store_id}

    def del_store(self):
        try:
            Store.objects.get(store_id=self.data['id']).delete()
            StoreGoods.objects.filter(store_id=self.data['id']).delete()
        except Exception as e:
            app.error(str(e) + '{}'.format(self.data['id']))
            return {'message': 'delete failed'}

        return {'message': 'ok'}

    def change_store(self):
        data = self.data
        try:
            this_store = Store.objects.get(store_id=data['id'])
            this_store.store_name = data['name']
            # this_store.store_phone = data['phone']
            # this_store.store_addr = data['addr']
            this_store.store_area = data['area']
            this_store.store_pay_type = data['pay_type']
            this_store.store_deposit = data['deposit']
            this_store.save()

            new_info = {'id': this_store.store_id, 'name': this_store.store_name,
                        'area': this_store.store_area, 'pay_type': this_store.store_pay_type,
                        'deposit': this_store.store_deposit}

            return {'message': 'ok', 'new_info': new_info}
        except Exception as e:
            app.error(str(e) + '{}'.format(data))
            return {'message': 'failed'}

    @staticmethod
    def get_store_area_id(store_id):
        try:
            store = Store.objects.get(store_id=store_id)
            return store.store_area
        except Exception as e:
            app.error(str(e))
            return None

    def setprice_store(self):
        price_list = self.data['goods_list']
        store_id = self.data['store_id']
        store_goods = StoreGoods.objects.filter(store_id=store_id)

        store_goods_list = [i.goods_id for i in store_goods]

        for goods in price_list:
            goods_id = goods['goods_id']
            goods_price = goods['goods_price']
            goods_stock = goods['goods_stock']

            try:
                goods_info = GoodsManager.get_goods_info(
                    goods_id=goods['goods_id'])
            except Exception as e:
                app.error(str(e))
                return {'message':'failed'}

            if goods['goods_id'] not in store_goods_list:
                new_price = StoreGoods(store_id=store_id,
                                       goods_id=goods_id,
                                       goods_price=goods_price,
                                       goods_stock=goods_stock)
                new_price.save()
            else:
                this_goods = StoreGoods.objects.get(
                    store_id=store_id, goods_id=goods_id)
                this_goods.goods_price = goods_price
                this_goods.save()

        return {'message': 'ok'}

    @staticmethod
    def all_store():
        all_store = Store.store_all()
        all_store_list = []
        for store in all_store:
            all_store_list.append({'id': store.store_id,
                                   'name': store.store_name,
                                   'phone': store.store_phone,
                                   'addr': store.store_addr,
                                   'area': store.store_area,
                                   'area_name': AreaManager.get_area_name(store.store_area),
                                   'pay_type': store.store_pay_type,
                                   'deposit': store.store_deposit})

        return {'message': 'ok', 'info': all_store_list}

    @staticmethod
    def get_store_price(store_id=0):
        all_store_price = StoreGoods.objects.filter(store_id=store_id)
        result = []
        for i in all_store_price:
            goods_info = GoodsManager.get_goods_info(goods_id=i.goods_id)
            result.append(
                {'goods_id': i.goods_id,
                 'goods_name': goods_info['goods_name'],
                 'goods_spec': goods_info['goods_spec'],
                 'goods_price': float(i.goods_price)})

        return result

    def getprice_store(self):
        goods_list = StoreManager.get_store_price(self.data['store_id'])
        return {'message': 'ok', 'goods_list': goods_list}

    def reply(self):
        method_name = self.action + '_store'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.info(str(e))
            return StoreManager.all_store()

    def __str__(self):
        return len(self.data)


class EmployeeManager(object):
    def __init__(self, action, postdata):
        self.action = action
        self.data = postdata

    def settype_employee(self):
        uid = self.data['uid']
        set_type = self.data['set_type']
        if self.data['set_type'] == 2:
            area_id = self.data['area_id']
            if not AreaManager.check_area_id_exist(area_id):
                return {'message': 'area_id error'}

        else:
            area_id = -1

        try:
            uid = base64.b64decode(uid.encode('utf-8'))
            uid = str(uid, 'utf-8')
        except Exception as e:
            app.info(str(e))
            return {'message': 'failed'}

        try:
            user = User.objects.get(wk=uid)
        except Exception as e:
            app.error(str(e))
            return {'message': 'failed'}

        UserManager.set_user_type(user, set_type=set_type, area_id=area_id)
        return {'message': 'ok'}

    @staticmethod
    def all_employee():
        all_employee = User.objects.filter(
            Q(user_type=0) | Q(user_type=1) | Q(user_type=2))

        all_employee_list = []
        for i in all_employee:
            all_employee_list.append(UserManager.get_user_info(i))

        return {'message': 'ok', 'employee_info': all_employee_list}

    def reply(self):
        method_name = self.action + '_employee'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.info(str(e))
            return EmployeeManager.all_employee()


class CustomerUserManager(object):
    """docstring for BindUserManager"""

    def __init__(self, postdata, user):
        self.data = postdata
        self.user = user

    def bind(self, store_id):
        user = self.user
        new_customer = CustomerProfile(wk=user, store_id=store_id)
        new_customer.save()
        if user.user_type <= 3:
            return {'message': 'failed'}

        user.user_type = 3
        user.save()

        return {'message': 'ok'}

    def reply(self):
        store_id = self.data['store_id']

        if not StoreManager.check_id_exist(store_id):
            return {'message': 'store_id not exist'}

        return self.bind(store_id)


class GoodsManager(object):
    """docstring for GoodsManager"""
    """
    action:
        add
        del
        change
        all
    TODO 完善
    """

    def __init__(self, postdata, action=all):
        self.data = postdata
        self.action = action

    def add_goods(self):
        goods_name = self.data['name']
        goods_spec = int(self.data['spec'])
        goods_stock = int(self.data['stock'])
        is_recover = int(self.data['recover'])

        new_goods = Goods(goods_name=goods_name,
                          goods_spec=goods_spec,
                          goods_stock=goods_stock,
                          is_recover=is_recover)
        new_goods.save()

        return {'message': 'ok', 'id': new_goods.goods_id}

    def del_goods(self):
        goods_id = self.data['id']
        try:
            Goods.objects.get(goods_id=goods_id).delete()
            return {'message': 'ok'}
        except Exception as e:
            app.info(str(e))
            return {'message': 'ok'}

    @staticmethod
    def all_goods():
        goods_all = Goods.goods_all()

        return_list = []
        for i in goods_all:
            return_list.append({'goods_id': i.goods_id,
                                'goods_name': i.goods_name,
                                'goods_spec': i.goods_spec,
                                'goods_stock': i.goods_stock,
                                'is_recover': i.is_recover})

        return {'message': 'ok', 'info': return_list}

    @staticmethod
    def get_goods_info(goods_id):
        goods = Goods.objects.get(goods_id=goods_id)
        return {'goods_id': goods.goods_id,
                'goods_name': goods.goods_name,
                'goods_spec': goods.goods_spec,
                'goods_stock': goods.goods_stock,
                'is_recover': goods.is_recover}

    # @staticmethod
    # def get_goods_info(goods_id):
    #     return Goods.objects.get(goods_id=goods_id).goods_name

    def reply(self):
        method_name = str(self.action) + '_goods'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.info(str(e))
            return GoodsManager.all_goods()


class OrderManager(object):
    def __init__(self, action, postdata, user):
        self.data = postdata
        self.action = action
        self.user = user

    @staticmethod
    def gen_order_id():
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + \
            str(random.randint(1000, 9999))

        return order_id

    def save_order(self):
        user = self.user
        order_id = OrderManager.gen_order_id()
        store_id = UserManager.get_user_store_id(user)
        area_id = StoreManager.get_store_area_id(store_id=store_id)
        remarks = self.data['remarks']

        total_price = self.save_order_detail(order_id, store_id)

        new_order = Order(
            order_id=order_id,
            store_id=store_id,
            user_id=user.wk,
            area_id=area_id,
            order_total_price=total_price,
            order_remarks=remarks
        )

        new_order.save()
        return {'message': 'ok', 'order_id': order_id}

    def save_order_detail(self, order_id, store_id):
        pack_goods = self.data['goods_list']
        order_all_goods = []
        order_price = 0

        for i in pack_goods:
            goods_id = i['goods_id']
            goods_count = i['goods_count']

            goods_info = GoodsManager.get_goods_info(goods_id=goods_id)
            this_goods = StoreGoods.objects.get(
                goods_id=goods_id,
                store_id=store_id
            )

            goods_price = this_goods.goods_price * goods_info['goods_spec']
            total_price = goods_price * goods_count
            order_price += total_price

            order_all_goods.append(
                OrderDetail(
                    order_id=order_id,
                    goods_id=goods_id,
                    goods_count=goods_count,
                    goods_price=goods_price,
                    total_price=total_price
                )
            )
            # pass

        OrderDetail.objects.bulk_create(order_all_goods)

        return order_price

    def get_older_detail(self):
        pass

    def set_order_status(self):
        pass

    def new_order(self):
        return self.save_order()

    def reply(self):
        method_name = self.action + '_order'
        # try:
        method = getattr(self, method_name)
        return method()
        # except Exception as e:
        #     print(e)
        #     return {'message': 'failed'}
