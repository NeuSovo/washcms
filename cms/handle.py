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
request_backup = logging.getLogger('app.backup')


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
            except Exception as e:
                result['code'] = ASEC.SESSION_NOT_WORK
                result['message'] = ASEC.getMessage(ASEC.SESSION_NOT_WORK)

                return parse_info(result)

            if user_key.expire_date < datetime.now():
                result['code'] = ASEC.SESSION_EXPIRED
                result['message'] = ASEC.getMessage(ASEC.SESSION_EXPIRED)

                return parse_info(result)

            user = UserManager.get_user(wckey=wckey)

            app.info("[{}][{}][{}][{}]".format(
                func.__name__, user.wk, action, user.user_type))

            request_backup.info(str(body))

            if user_type == -1 or user.user_type <= user_type:
                return func(*args, **kwargs, user=user)
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
            app.error(str(e))
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
        if have_user.exists():
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
        try:
            this_user = Session.objects.get(session_key=self.openid)
        except Exception as e:
            this_user = Session()

        sess = WechatSdk.gen_hash()

        this_user.we_ss_key = self.wxsskey
        this_user.session_data = sess
        this_user.expire_date = datetime.now() + timedelta(days=3)
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
        if time.time() - int(checktime) > 5:
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

        if not settings.DEBUG:
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
    def get_user_store(user):
        """
        User_type must be 3
        :param user:
        :return: Customer User store id
        """
        return CustomerProfile.objects.get(wk=user).store

    @staticmethod
    def get_user_area(user):
        """
        User_type must be 2
        :param user:
        :return: Courier User Area id
        """
        return PeisongProfile.objects.get(wk=user).area

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
        store = UserManager.get_user_store(user)

        store.store_addr = profile['addr']
        store.store_phone = int(profile['phone'])
        store.store_name = profile['name']
        store.save()

        return store

    @staticmethod
    def get_user_store_profile(user):
        """
        only user type is 3
        """
        profile = {}
        store = UserManager.get_user_store(user)

        profile['addr'] = store.store_addr
        profile['phone'] = store.store_phone
        profile['name'] = store.store_name

        return profile

    @staticmethod
    def set_user_peisong_profile(user, profile):
        try:
            phone = int(profile['phone'])
        except Exception as e:
            app.info(str(e))
            return

        peisong = PeisongProfile.objects.get(wk=user)
        peisong.name = profile['name']
        peisong.phone = phone
        peisong.save()

        return peisong

    @staticmethod
    def get_user_peisong_profile(user):
        peisong = PeisongProfile.objects.get(wk=user)
        return {'area_id': peisong.area.id,
                'area_name': peisong.area.area_name,
                'name': peisong.name,
                'phone': peisong.phone}

    @staticmethod
    def set_user_type(user, set_type, area=None):
        """
        set_type = 0,1,2PeisongProfile
        """
        if set_type == 2:
            PeisongProfile(wk=user, area=area).save()

        if set_type == 4:
            if user.user_type == 2:
                to_delete = PeisongProfile.objects.get(wk=user)
                for i in PickOrder.objects.filter(pick_user=PeisongProfile.objects.get(wk=user)):
                    PickOrderDetail.objects.filter(
                        order_id=i.order_id).delete()
                    i.delete()
                to_delete.delete()

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
            if PeisongProfile.objects.filter(area=to_delete).exists():
                return {'message': '请确保此区域下已没有配送员'}

            if Store.objects.filter(store_area=to_delete).exists():
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

        try:
            area = DeliveryArea.objects.get(id=int(data['area']))
        except Exception as e:
            return {'message': 'failed'}

        new_store = Store(store_id=store_id,
                          store_name=data['name'],
                          # store_phone=data['phone'],
                          # store_addr=data['addr'],
                          store_area=area,
                          store_pay_type=data['pay_type'],
                          store_deposit=data['deposit'])

        new_store.save()

        return {'message': 'ok', 'id': new_store.store_id}

    def del_store(self):
        try:
            to_delete = Store.objects.get(store_id=int(self.data['id']))
            StoreGoods.objects.filter(store=to_delete).delete()
            order_pool = Order.objects.filter(store=to_delete)

            # delete Store Order and Order detail
            for i in order_pool:
                OrderDetail.objects.filter(order_id=i.order_id).delete()
                i.delete()

            # delete Store User
            cus_user = CustomerProfile.objects.filter(store=to_delete)
            for i in cus_user:
                UserManager.set_user_type(i.wk, 4)
                i.delete()

            to_delete.delete()

        except Exception as e:
            app.error(str(e) + '{}'.format(self.data['id']))
            return {'message': 'delete failed'}

        return {'message': 'ok'}

    def change_store(self):
        data = self.data
        try:
            this_store = Store.objects.get(store_id=int(data['id']))
            this_store.store_name = data['name']
            # this_store.store_phone = data['phone']
            # this_store.store_addr = data['addr']
            this_store.store_area = DeliveryArea.objects.get(id=data['area'])
            this_store.store_pay_type = int(data['pay_type'])
            this_store.store_deposit = data['deposit']
            this_store.save()

            new_info = {'id': this_store.store_id,
                        'name': this_store.store_name,
                        'area': this_store.store_area.area_name,
                        'pay_type': this_store.store_pay_type,
                        'deposit': this_store.store_deposit}

            return {'message': 'ok', 'new_info': new_info}
        except Exception as e:
            app.error(str(e) + '{}'.format(data))
            return {'message': 'failed'}

    def getprice_store(self):
        try:
            store = Store.objects.get(store_id=self.data['store_id'])
        except Exception as e:
            return {'message': 'store_id not exist'}

        goods_list = StoreManager.get_store_price(store)
        return {'message': 'ok', 'goods_list': goods_list}

    def setprice_store(self):
        try:
            price_list = self.data['goods_list']
            store_id = int(self.data['store_id'])
        except Exception as e:
            return {'message': str(e)}

        try:
            store = Store.objects.get(store_id=store_id)
            store_goods = StoreGoods.objects.filter(store=store)
        except Exception as e:
            return {'message': str(e)}

        store_goods_list = [i.goods_id for i in store_goods]

        for goods in price_list:
            goods_id = goods['goods_id']
            goods_price = goods['goods_price']
            goods_stock = goods['goods_stock']

            try:
                t_goods = Goods.objects.get(goods_id=goods_id)
            except Exception as e:
                app.error(str(e))
                return {'message': 'failed'}

            if goods['goods_id'] not in store_goods_list:
                new_price = StoreGoods(store=store,
                                       goods=t_goods,
                                       goods_stock=goods_stock,
                                       goods_price=goods_price)
                new_price.save()
            else:
                this_goods = StoreGoods.objects.get(
                    store=store, goods=t_goods)
                this_goods.goods_price = goods_price
                this_goods.save()

        return {'message': 'ok'}

    @staticmethod
    def all_store():
        all_store = Store.store_all()
        all_store_list = []
        for store in all_store:
            all_store_list.append(StoreManager.get_store_info(store))

        return {'message': 'ok', 'info': all_store_list}

    @staticmethod
    def get_store_price(store):
        all_store_price = StoreGoods.objects.filter(store=store)
        result = []
        for i in all_store_price:
            result.append(
                {'goods_id': i.goods.goods_id,
                 'goods_name': i.goods.goods_name,
                 'goods_spec': i.goods.goods_spec,
                 'goods_price': float(i.goods_price),
                 'goods_stock': i.goods.goods_stock,
                 'goods_store_stock': i.goods_stock,
                 'is_recover': i.goods.is_recover})

        return result

    @staticmethod
    def get_store_info(store):
        return {'id': store.store_id,
                'name': store.store_name,
                'area': store.store_area.id,
                'area_name': store.store_area.area_name,
                'phone': store.store_phone,
                'addr': store.store_addr,
                'deposite': store.store_deposit,
                'pay_type': store.store_pay_type}

    @staticmethod
    def sync_store_stock(order):
        # TODO
        # Sync Car Stock
        goods_pool = OrderDetail.objects.filter(order_id=order.order_id)

        for i in goods_pool:
            store_goods = StoreGoods.objects.get(
                store=order.store, goods=i.goods)
            car_goods = PeisongCarStock.objects.get()
            store_goods.goods_stock += i.goods_count
            store_goods.save()

        return {'message': 'ok'}

    def reply(self):
        method_name = self.action + '_store'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.info(str(e))
            return StoreManager.all_store()


class EmployeeManager(object):
    def __init__(self, action, postdata):
        self.action = action
        self.data = postdata

    def settype_employee(self):
        uid = self.data.get('uid', 0)
        set_type = int(self.data.get('set_type', -1))

        if set_type < 0:
            return {'message': 'failed'}

        if self.data['set_type'] == 2:
            area_id = int(self.data.get('area_id', 0))
            try:
                area = DeliveryArea.objects.get(id=area_id)
            except Exception as e:
                return {'message': 'area not exist'}

        else:
            area = None

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

        UserManager.set_user_type(user, set_type=set_type, area=area)
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

    def bind(self, store):
        """
        [TODO] Rebind 
        """
        user = self.user

        if user.user_type < 3:
            return {'message': 'failed'}

        new_customer = CustomerProfile(wk=user, store=store)
        new_customer.save()

        user.user_type = 3
        user.save()

        return {'message': 'ok'}

    def reply(self):
        store_id = int(self.data.get('store_id', 0))

        try:
            store = Store.objects.get(store_id=store_id)
        except Exception as e:
            app.info(str(e))
            return {"message": 'store_id not exist'}

        return self.bind(store)


class GoodsManager(object):
    """docstring for GoodsManager
    """

    def __init__(self, postdata, action=all):
        self.data = postdata
        self.action = action

    @staticmethod
    def sync_goods_stock(order):
        goods_pool = PickOrderDetail.objects.filter(order_id=order.order_id)
        try:
            for i in goods_pool:
                i.goods.goods_stock -= i.goods_count

                try:
                    car_goods = PeisongCarStock.objects.get(
                        wk=order.pick_user, goods=i.goods)
                    car_goods.goods_stock += i.goods_count
                    car_goods.save()
                except:
                    car_goods = PeisongCarStock(
                        wk=order.pick_user, goods=i.goods, goods_stock=i.goods_count)
                    car_goods.save()

                i.goods.save()
        except Exception as e:
            app.error(str(e))
            return {'message': (str(e))}

        return {'message': 'ok'}

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
        goods_id = int(self.data['goods_id'])
        Goods.objects.get(goods_id=goods_id).delete()
        StoreGoods.objects.filter(goods_id=goods_id).delete()

        return {'message': 'ok'}

    def set_goods(self):
        goods_id = int(self.data['goods_id'])
        try:
            this_goods = Goods.objects.get(goods_id=goods_id)
            this_goods.goods_stock = self.data['stock']
            this_goods.save()
            return {'message': 'ok'}
        except Exception as e:
            app.info(str(e))
            return {'message': 'failed'}

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
        store = UserManager.get_user_store(user)
        area = store.store_area
        remarks = self.data['remarks']

        def save_order_detail(order_id, store):
            """
            TODO despoit
            """
            pack_goods = self.data['goods_list']
            order_all_goods = []
            order_price = 0

            for i in pack_goods:
                goods_id = i['goods_id']
                goods_count = i['goods_count']

                goods = Goods.objects.get(goods_id=goods_id)
                this_goods = StoreGoods.objects.get(
                    goods=goods,
                    store=store
                )
                goods_price = this_goods.goods_price * goods.goods_spec

                total_price = goods_price * int(goods_count)
                order_price += total_price
                order_all_goods.append(
                    OrderDetail(
                        order_id=order_id,
                        goods=goods,
                        goods_count=goods_count,
                        goods_price=goods_price,
                        total_price=total_price
                    )
                )
                # pass

            OrderDetail.objects.bulk_create(order_all_goods)

            return order_price

        total_price = save_order_detail(order_id, store)

        new_order = Order(
            order_id=order_id,
            store=store,
            user=CustomerProfile.objects.get(wk=self.user),
            area=area,
            pay_type=store.store_pay_type,
            order_total_price=total_price,
            order_remarks=remarks
        )

        new_order.save()
        return {'message': 'ok', 'order_id': order_id}

    @staticmethod
    def get_order_goods_detail(order_id):
        result = []
        goods = OrderDetail.objects.filter(order_id=order_id)

        for i in goods:
            result.append({'goods_id': i.goods.goods_id,
                           'goods_name': i.goods.goods_name,
                           'goods_spec': i.goods.goods_spec,
                           'goods_count': i.goods_count,
                           'total_price': str(i.total_price)})

        return result

    @staticmethod
    def get_order_simple_detail(order_id):
        order = Order.objects.get(order_id=order_id)
        return {
            'order_id': str(order.order_id),
            'create_time': str(order.create_time),
            'create_timestamp': time.mktime(order.create_time.timetuple()),
            'order_type': order.order_type,
            'pay_type': order.pay_type,
            'order_total_price': str(order.order_total_price),
            'receive_time': str(order.receive_time),
            'pay_from': order.pay_from,
            'remarks': order.order_remarks,
            'done_time': str(order.done_time)
        }

    @staticmethod
    def set_order_status(order, order_type, pay_from=None):
        max_cancel_minutes = timedelta(minutes=15)
        order_type = int(order_type)

        # 向上级跳 Refuse
        if order_type != 3 and order.order_type <= order_type:
            return {'message': 'failed'}

        # 大于取消时间 Refuse
        if order_type == 3:
            if datetime.now() - order.create_time > max_cancel_minutes:
                return {'message': 'failed'}

        # 待支付
        if order_type == 1:
            order.receive_time = datetime.now()
            try:
                StoreManager.sync_store_stock(order)
            except Exception as e:
                return {'message': 'failed'}

        if order_type == 0:
            order.done_time = datetime.now()
            if pay_from is None:
                return {'message': 'failed'}

            if order.pay_type == 1 and pay_from != 2:
                return {'message': '月结订单支付方式只能是月结'}

            order.pay_from = pay_from

        order.order_type = order_type
        order.save()

        return {'message': 'ok'}

    def new_order(self):
        return self.save_order()

    def detail_order(self):
        order_id = int(self.data['order_id'])
        order_info = OrderManager.get_order_simple_detail(order_id)

        order_goods = OrderManager.get_order_goods_detail(order_id)
        return {'message': 'ok',
                'info': order_info,
                'goods': order_goods}

    def cancel_order(self):
        order_id = int(self.data.get('order_id', 0))
        try:
            order = Order.objects.get(order_id=order_id)
        except Exception as e:
            return {'message': 'order_id failed'}

        return OrderManager.set_order_status(order, 3)

    def status_order(self):
        status = int(self.data['status'])
        store = UserManager.get_user_store(user=self.user)
        status_order = []

        if status > 3:
            return {'message': 'failed'}

        order_list = Order.objects.filter(
            store=store, order_type=status)

        for i in order_list:
            status_order.append(
                OrderManager.get_order_simple_detail(i.order_id))

        return {'message': 'ok', 'info': status_order}

    def reply(self):
        method_name = self.action + '_order'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.info(str(e))
            return {'message': str(e)}


class PeiSongManager(object):
    def __init__(self, user, postdata):
        self.user = user
        self.data = postdata
        self.area = UserManager.get_user_area(user)

    @staticmethod
    def set_pick_order_status(order, status):
        pass

    @staticmethod
    def get_peisong_order_info(order):
        peisong_detail = {}
        store_info = StoreManager.get_store_info(store=order.store)
        goods_info = OrderManager.get_order_goods_detail(
            order_id=order.order_id)

        peisong_detail['order_info'] = {}
        peisong_detail['order_info']['order_id'] = str(order.order_id)
        peisong_detail['order_info']['create_time'] = str(order.create_time)
        peisong_detail['order_info']['receive_time'] = str(order.receive_time)
        peisong_detail['order_info']['order_total_price'] = str(
            order.order_total_price)
        peisong_detail['order_info']['pay_type'] = order.pay_type
        peisong_detail['order_info']['remarks'] = order.order_remarks

        peisong_detail['goods_info'] = goods_info

        peisong_detail['store_info'] = {}
        peisong_detail['store_info']['name'] = store_info['name']
        peisong_detail['store_info']['phone'] = store_info['phone']
        peisong_detail['store_info']['addr'] = store_info['addr']

        return peisong_detail

    @staticmethod
    def get_pick_order_info(order):
        order_info = {}
        goods_info = []

        order_info['order_id'] = str(order.order_id)
        order_info['create_time'] = str(order.create_time)
        order_info['order_type'] = order.order_type
        order_info['confirm_time'] = str(order.confirm_time)
        order_info['is_modify'] = order.is_modify

        for i in order.get_order_detail():
            goods_info.append({
                'goods_id': i.goods.goods_id,
                'goods_name': i.goods.goods_name,
                'goods_spec': i.goods.goods_spec,
                'goods_count': i.goods_count
            }
            )
        return {'order_info': order_info,
                'goods_info': goods_info}

    def get_receive_peisong(self):
        """
        [TODO] Redis

        """
        result = {}
        info = []
        order_pool = Order.objects.filter(area=self.area, order_type=2)

        for i in order_pool:
            peisong_detail = PeiSongManager.get_peisong_order_info(i)

            info.append(peisong_detail)

        result['message'] = 'ok'
        result['info'] = info

        return result

    def set_receive_peisong(self):
        order_id = int(self.data.get('order_id', 0))

        try:
            order = Order.objects.get(order_id=order_id)
        except Exception as e:
            return {'message': 'order_id failed'}

        res = OrderManager.set_order_status(order, 1)
        if res['message'] != 'ok':
            return res

        return {'message': 'ok'}

    def get_pay_peisong(self):
        result = {}
        info = []
        order_pool = Order.objects.filter(
            area=self.area, order_type=1, pay_type=0)

        for i in order_pool:
            peisong_detail = PeiSongManager.get_peisong_order_info(i)

            info.append(peisong_detail)

        def receive(s):
            return s['order_info']['receive_time']

        info = sorted(info, key=receive, reverse=True)

        result['message'] = 'ok'
        result['info'] = info

        return result

    def set_pay_peisong(self):
        order_id = int(self.data.get('order_id', 0))
        pay_from = int(self.data.get('pay_from', None))

        try:
            order = Order.objects.get(order_id=order_id)
        except Exception as e:
            return {'message': 'order_id failed'}

        res = OrderManager.set_order_status(order, 0, pay_from=pay_from)

        if res['message'] != 'ok':
            return res

        return {'message': 'ok'}

    def get_car_stock(self):
        result = []
        pick_user = PeisongProfile.objects.get(wk=self.user)
        goods_pool = PeisongCarStock.objects.filter(wk=pick_user)
        for i in goods_pool:
            result.append({'goods_id': i.goods.goods_id,
                           'goods_name': i.goods.goods_name,
                           'goods_spec': i.goods.goods_spec,
                           'goods_stock': int(i.goods_stock)})
        return {'message': 'ok',
                'info': result}

    def get_ps_stock(self):
        # pass
        order_pool = Order.objects.filter(area=self.area, order_type=2)
        result = []

        info = OrderDetail.objects.raw('select 1 as id,goods_id,sum(goods_count) as goods_count \
                                        from cms_orderdetail where cms_orderdetail.order_id in \
                                        (select order_id from cms_order where order_type={} and area_id={}) \
                                        group by cms_orderdetail.goods_id'.format(2, self.area.id))

        for i in info:
            print(i.goods_id.goods_name)
            goods_info = GoodsManager.get_goods_info(i.goods_id)
            result.append({'goods_id': i.goods_id,
                           'goods_name': goods_info['goods_name'],
                           'goods_spec': goods_info['goods_spec'],
                           'goods_count': int(i.goods_count)})

        return {'message': 'ok',
                'info': result}

    def new_pick(self):
        order_id = OrderManager.gen_order_id()
        pick_user = PeisongProfile.objects.get(wk=self.user)

        def save_pick_detail(order_id, goods_list):
            pickorder_all_goods = []
            for i in goods_list:
                goods_id = i['goods_id']
                goods_count = i['goods_count']

                try:
                    goods = Goods.objects.get(goods_id=goods_id)
                except Exception as e:
                    app.info(str(e))
                    return {'message': 'goods_id does not exist'}

                pickorder_all_goods.append(
                    PickOrderDetail(
                        order_id=order_id,
                        goods=goods,
                        goods_count=goods_count
                    )
                )
            try:
                PickOrderDetail.objects.bulk_create(pickorder_all_goods)
            except Exception as e:
                app.error(str(e))
                return {'message': 'failed'}

            return {'message': 'ok'}

        info = save_pick_detail(order_id, self.data['goods_list'])
        if info['message'] != 'ok':
            return info

        PickOrder(order_id=order_id, pick_user=pick_user).save()
        info['order_id'] = order_id

        return info

    def get_pick(self):
        # filter all order
        # todo order_type = 1
        info = []
        pick_user = PeisongProfile.objects.get(wk=self.user)
        order_pool = PickOrder.objects.filter(pick_user=pick_user)

        for i in order_pool:
            info.append(PeiSongManager.get_pick_order_info(i))

        return {'message': 'ok',
                'info': info}


class KuGuanManager(object):
    """docstring for KuGuanManager"""

    def __init__(self, postdata, user):
        self.data = postdata
        self.user = user

    def get_pick(self):
        order_pool = PickOrder.objects.filter(order_type=1)
        info = []
        for i in order_pool:
            t_info = PeiSongManager.get_pick_order_info(i)
            t_info['user_info'] = {}
            t_info['user_info']['user_name'] = i.pick_user.name
            t_info['user_info']['user_phone'] = i.pick_user.phone
            info.append(t_info)

        return {'message': 'ok',
                'info': info}

    def confirm_pick(self):
        order_id = int(self.data.get('order_id', 0))

        try:
            order = PickOrder.objects.get(order_id=order_id)
        except:
            return {'message': 'order_id error'}

        # todo goods_list

        info = GoodsManager.sync_goods_stock(order)
        if info['message'] == 'ok':
            order.order_type = 0
            order.confirm_time = datetime.now()
            order.confirm_user = self.user
            order.save()

        return info

    def modify_pick(self):
        order_id = int(self.data.get('order_id', 0))

        try:
            order = PickOrder.objects.get(order_id=order_id)
        except:
            return {'message': 'order_id error'}

        goods_list = self.data['goods_list']

        for i in goods_list:
            try:
                o = PickOrderDetail.objects.get(
                    order_id=order_id, goods_id=i['goods_id'])
            except Exception as e:
                return {'message': 'goods_id({}) not exist'.format(i['goods_id'])}
            o.goods_count = i['goods_count']
            o.save()

        order.is_modify = 1
        order.save()
        return dict({'message': 'ok'}, **(PeiSongManager.get_pick_order_info(order)))
