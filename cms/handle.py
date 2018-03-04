# -*- coding: utf-8 -*-
import os
import json
import time
import base64
import random
import logging
import requests
from hashlib import sha256, md5

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
    parmer must be a dict
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
                body = json.loads(request.body)
                wckey = body['base_req']['wckey']
                print("backup data : {}:{}".format(func.__name__, body))
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

            user = User.objects.get(wk=user_key.session_key)

            if user_type == -1 or user.user_type <= user_type:
                return func(request)
            else:
                return parse_info({'message': 'user_type failed'})

        return inner_wrapper
    return wrapper


class WechatSdk(object):
    __Appid = 'wx5c7d55175f3872b7'
    __SECRET = '18e18b264801eb53c9fe7634504f2f15'
    """
    WechatSdk
    Based on Wechat user code
    """

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
        s = requests.Session()
        params = {
            'appid': self.__Appid,
            'secret': self.__SECRET,
            'js_code': self.code,
            'grant_type': 'authorization_code'
        }

        try:
            data = s.get(
                'https://api.weixin.qq.com/sns/jscode2session', params=params)
        except Exception as e:
            app.error(str(e) + '\tcode:' + str(self.code))
            return False

        info = data.json()

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

    def __init__(self, wckey):
        super(LoginManager, self).__init__()
        self.wckey = wckey

    def __str__(self):
        return self.wckey

    #
    def check(self, sign, checktime):
        if time.time() - int(checktime) > 30:
            return False

        to_check_str = str(checktime) + str(self.TOKEN)
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

    def get_info(self, user):
        name = user.nick_name
        avatar_links = user.avatar_links

        return {'name': name,
                'avatar_links': avatar_links,
                'qrcod': LoginManager.gen_base64(user.wk)}  # 'https://pan.baidu.com/share/qrcode?url=' + self.gen_base64(user.wk)}

    def reply(self):

        user = get_user(self.wckey)

        user_info = self.get_info(user)

        return {'code': ASEC.LOGIN_SUCCESS,
                'user_type': user.user_type,
                'info': user_info,
                'message': ASEC.getMessage(ASEC.LOGIN_SUCCESS)}


class AreaManager(object):
    def __init__(self, action, postdata):
        self.wckey = postdata['base_req']['wckey']
        self.action = action
        self.data = postdata

    def add_area(self):
        """
            post name
        """
        new_area = DeliveryArea(area_name=self.data['name'])
        new_area.save()

        return {'message': 'ok', 'id': new_area.id}

    def del_area(self):
        """
            post id
        """
        try:
            DeliveryArea.objects.get(id=self.data['id']).delete()
        except Exception as e:
            app.info(str(e))
            return {'message': 'delete failed'}

        return {'message': 'ok'}

    def change_area(self):
        """
             post id,new_name
        """
        area = DeliveryArea.objects.get(id=self.data['id'])
        area.area_name = self.data['name']
        area.save()
        return {'message': 'ok', 'new_name': area.area_name}

    @staticmethod
    def all_area():
        """
            None
        """
        allarea = DeliveryArea.area_all()
        all_area_list = []
        for _i in allarea:
            all_area_list.append({'id': _i.id,
                                  'name': _i.area_name})

        return {'message': 'ok',
                'info': all_area_list}

    def reply(self):
        user = get_user(self.wckey)

        method_name = self.action + '_area'
        try:
            method = getattr(self, method_name)
            return method()
        except:
            return AreaManager.all_area()


class StoreManager(object):
    """docstring for StoreManager"""

    def __init__(self, action, postdata):
        super(StoreManager, self).__init__()
        self.wckey = postdata['base_req']['wckey']
        self.action = action
        self.data = postdata

    def add_store(self):
        data = self.data
        new_store = Store(store_name=data['name'],
                          store_phone=data['phone'],
                          store_addr=data['addr'],
                          store_area=data['area'],
                          store_pay_type=data['pay_type'],
                          store_deposit=data['deposit'])

        new_store.save()

        return {'message': 'ok', 'id': new_store.store_id}

    def del_store(self):
        try:
            Store.objects.get(store_id=self.data['id']).delete()
        except Exception as e:
            app.error(str(e) + '{}'.format(self.data['id']))
            return {'message': 'delete failed'}

        return {'message': 'ok'}

    def change_store(self):
        data = self.data
        try:
            this_store = Store.objects.get(store_id=data['id'])
            this_store.store_name = data['name']
            this_store.store_phone = data['phone']
            this_store.store_addr = data['addr']
            this_store.store_area = data['area']
            this_store.store_pay_type = data['pay_type']
            this_store.store_deposit = data['deposit']
            this_store.save()
            new_info = {'id': this_store.store_id,
                        'name': this_store.store_name,
                        'phone': this_store.store_phone,
                        'addr': this_store.store_addr,
                        'area': this_store.store_area,
                        'pay_type': this_store.store_pay_type,
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
        price_list = self.data['goods_price']
        user = get_user(wckey=self.wckey)
        store_id= self.data['store_id']
        store_goods = StoreGoods.objects.filter(store_id=store_id)

        store_goods_list = [i.goods_id for i in store_goods]

        for goods in price_list:
            goods_id = goods['goods_id']
            goods_price = goods['goods_price']
            goods_stock = goods['goods_stock']
            goods_info = GoodsManager.get_goods_info(goods_id=goods['goods_id'])
            if goods['goods_id'] not in store_goods_list:
                StoreGoods(store_id=store_id,goods_id=goods_id,goods_name=goods_info['goods_name'],
                            goods_price=goods_price,goods_stock=goods_stock,
                            goods_spec=goods_info['goods_spec']).save()
            else:
                this_goods = StoreGoods.objects.get(goods_id=goods_id)
                this_goods.goods_price = goods_price
                this_goods.save()

        return {'message':'ok'}

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
                                   'pay_type': store.store_pay_type,
                                   'deposit': store.store_deposit})

        return {'message': 'ok', 'info': all_store_list}

    @staticmethod
    def get_store_price(store_id):
        all_store_price = StoreGoods.objects.filter(store_id=store_id)
        result = []
        for i in all_store_price:
            result.append({'id': i.goods_id,'spec': i.goods_spec,'price': i.goods_price})

        return result

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


class SetUserManager(object):
    def __init__(self, postdata):
        self.data = postdata

    def set_user(self, uid, set_type, area_id=-1):
        try:
            uid = base64.b64decode(uid.encode('utf-8'))
            uid = str(uid, 'utf-8')
        except Exception as e:
            app.info(str(e))
            return {'message': 'failed'}

        try:
            user = User.objects.get(wk=uid)
        except:
            return {'message': 'failed'}

        if set_type > 3:
            return {'message': 'failed'}

        if set_type == 2:
            CourierProfile(wk=user, area_id=area_id).save()

        user.user_type = set_type
        user.save()
        return {'message': 'ok'}

    def reply(self):
        uid = self.data['uid']
        set_type = self.data['set_type']
        if self.data['set_type'] == 1:
            area_id = self.data['area_id']
        else:
            area_id = -1

        return self.set_user(uid, set_type, area_id)


class CustomerUserManager(object):
    """docstring for BindUserManager"""

    def __init__(self, postdata):
        self.data = postdata
        self.wk = postdata['base_req']['wckey']

    @staticmethod
    def check_id_exist(store_id):
        try:
            Store.objects.get(store_id=store_id)
            return True
        except Exception as e:
            app.info(str(e))
            return False

    def bind(self, user, store_id):
        new_customer = CustomerProfile(wk=user, store_id=store_id)
        new_customer.save()
        if user.user_type <= 3:
            return {'message': 'failed'}

        user.user_type = 3
        user.save()
        
        return {'message': 'ok'}

    @staticmethod
    def get_user_store_id(user):
        try:
            store_user = CustomerProfile.objects.get(wk=user)
            return store_user.store_id
        except Exception as e:
            return None

    def reply(self):
        store_id = self.data['store_id']

        if not CustomerUserManager.check_id_exist(store_id):
            return {'message': 'store_id not exist'}

        user = get_user(wckey=self.wk)

        return self.bind(user, store_id)


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
    def __init__(self, postdata,action = all):
        self.data = postdata
        self.action = action
        
    def add_goods(self):
        goods_name = self.data['name']
        goods_spec = self.data['spec']
        goods_stock = self.data['stock']
        is_recover = self.data['recover']
        new_goods = Goods(goods_name=goods_name,goods_spec=goods_spec,goods_stock=goods_stock,is_recover=is_recover)
        new_goods.save()

        return {'message': 'ok','id': new_goods.goods_id}

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
            return_list.append({'goods_id': i.goods_id,'goods_name': i.goods_name,'goods_spec': i.goods_spec,
                                'goods_stock': i.goods_stock,'is_recover': i.is_recover})

        return {'message': 'ok','info': return_list}

    @staticmethod
    def get_goods_info(goods_id):
        goods = Goods.objects.get(goods_id=goods_id)
        return {'goods_id': goods.goods_id,'goods_name': goods.goods_name,'goods_spec': goods.goods_spec,
                                'goods_stock': goods.goods_stock,'is_recover': goods.is_recover}

    def reply(self):
        method_name = self.action + '_goods'
        try:
            method = getattr(self, method_name)
            return method()
        except :
            return GoodsManager.all_goods()


class OrderManager(object):
    def __init__(self, action, postdata):
        self.data = postdata
        self.action = action
        self.wckey = postdata['base_req']['wckey']

    @staticmethod
    def gen_order_id():
        order_id = datetime.now().strftime("%Y%m%d%H%M%S") + str(random.randint(1000, 9999))

        return order_id

    def save_order(self):
        user = get_user(wckey=self.wckey)
        order_id = OrderManager.gen_order_id()
        store_id = CustomerUserManager.get_user_store_id(user)
        area_id = StoreManager.get_store_area_id(store_id=store_id)
        remarks = self.data['remarks']
        total_price = self.save_order_detail(order_id,store_id)

        new_order = Order(order_id=order_id,store_id=store_id,user_id=user.wk,area_id=area_id,
                        order_total_price=total_price,order_remarks=remarks)
        new_order.save()
        return {'message':'ok','order_id':order_id}

    def save_order_detail(self,order_id,store_id):
        pack_goods = self.data['pack_goods']
        order_all_goods = []
        # goods_price = StoreManager.get_store_price(self.store_id)
        order_price = 0
        for i in pack_goods:
            goods_id = i['goods_id']
            goods_count = i['goods_count']
            this_goods = StoreGoods.objects.get(goods_id=goods_id, store_id=store_id)
            goods_price = this_goods.goods_price * this_goods.goods_spec
            total_price = goods_price * goods_count
            order_price += total_price
            order_all_goods.append(OrderDetail(order_id=order_id, goods_id=goods_id, 
                        goods_count=goods_count, goods_price=goods_price, total_price=total_price))
            # pass

        OrderDetail.objects.bulk_create(order_all_goods)

        return order_price

    def get_old_detail(self):
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
