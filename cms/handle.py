# -*- coding: utf-8 -*-
import os
import random
import logging

from datetime import datetime, timedelta

from cms.tools import *
from cms.models import *

from django.db.models import Q
from django.conf import settings

from cms.apps import APIServerErrorCode as ASEC
from cms.auth import UserManager, LoginManager, WechatSdk


app = logging.getLogger('app.custom')


class AreaManager(object):
    def __init__(self, postdata):
        self.data = postdata

    def add_area(self):
        try:
            new_area = DeliveryArea(area_name=self.data['name'])
            new_area.save()
        except Exception:
            app.info(Exception("add_area Type Errror"))
            return {'message': '错误参数'}

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
        area_id = int(self.data.get('id', 0))
        try:
            area = DeliveryArea.objects.get(id=area_id)
        except Exception:
            return {'message': '区域id不存在'}

        area.area_name = self.data['name']
        area.save()
        return {'message': 'ok', 'new_name': area.area_name}

    @staticmethod
    def all_area():
        all_area = DeliveryArea.area_all()
        all_area_list = list()

        for _i in all_area:
            all_area_list.append({'id': _i.id,
                                  'name': _i.area_name})

        return {'message': 'ok',
                'info': all_area_list}


class StoreManager(object):
    """docstring for StoreManager"""

    def __init__(self, postdata, action=None, user=None):
        self.action = action
        self.data = postdata
        self.user = user

    @staticmethod
    def check_id_exist(store_id):
        try:
            Store.objects.get(store_id=store_id)
            return True
        except Exception:
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
        area_id = int(data.get('area', 0))
        deposit = int(data.get('deposit', 0))
        name = data.get('name')
        pay_type = data.get('pay_type', 0)

        try:
            area = DeliveryArea.objects.get(id=area_id)
        except Exception:
            return {'message': '区域id不存在'}
        has_deposit = 1 if deposit else 0
        new_store = Store(store_id=store_id,
                          store_name=name,
                          # store_phone=data['phone'],
                          # store_addr=data['addr'],
                          store_area=area,
                          store_pay_type=pay_type,
                          store_deposit=deposit,
                          has_deposit=has_deposit)

        new_store.save()
        return {'message': 'ok', 'id': new_store.store_id}

    def del_store(self):
        # [TODO]
        # 删除动作加入消息队列
        # 减少用户访问时间
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
            return {'message': '删除失败'}

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

            new_info = this_store.info()

            return {'message': 'ok', 'new_info': new_info}
        except Exception as e:
            app.error(str(e) + '{}'.format(data))
            return {'message': '保存失败 \n' + str(e)}

    def getprice_store(self):
        try:
            store = Store.objects.get(store_id=self.data['store_id'])
        except Exception as e:
            return {'message': '商户id不存在'}

        goods_list = store.price()
        return {'message': 'ok', 'goods_list': goods_list}

    def setprice_store(self):
        try:
            price_list = self.data['goods_list']
            store_id = int(self.data['store_id'])
        except Exception:
            return {'message': '参数错误'}

        try:
            store = Store.objects.get(store_id=store_id)
            store_goods = store.price()
        except Exception as e:
            return {'message': '商户id不存在'}

        store_goods_list = [i['goods_id'] for i in store_goods]
        for goods in price_list:
            goods_id = goods['goods_id']
            goods_price = goods['goods_price']
            goods_stock = goods['goods_stock']

            try:
                t_goods = Goods.objects.get(goods_id=goods_id)
            except Exception as e:
                app.error(str(e))
                return {'message': '商品不存在'}

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

        return {'message': 'ok', 'new_price': store.price()}

    @staticmethod
    def store_report_info(order_pool, recover_order_pool):
        money_sum = no_done_sum = no_pay_sum = 0

        for i in order_pool.iterator():
            money_sum += i.order_total_price
            if i.order_type != 0:
                no_done_sum += 1
                no_pay_sum += i.order_total_price

        info = {
            'order_sum': len(order_pool),
            'recover_sum': len(recover_order_pool),
            'money_sum': str(money_sum),
            'no_done_sum': no_done_sum,
            'no_pay_sum': str(no_pay_sum)
        }

        return info

    def month_store_report(self):
        user_store = UserManager.get_user_store(self.user).store

        today = datetime.now()
        month = self.data.get('month', today.month)
        if month <= 0 or month > 12:
            month = today.month

        key = str(user_store.store_id) + '_' + \
            str(month) + '_month_store_report'
        # Redis
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        order_pool = Order.objects.filter(order_type__lt=2,
                                          store=user_store, receive_time__month=month)
        recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                         store=user_store, receive_time__month=month)

        info = StoreManager.store_report_info(
            order_pool=order_pool, recover_order_pool=recover_order_pool)
        result = {'message': 'ok', 'info': info}

        if info['order_sum'] != 0:
            print('new_redis')
            redis_report.set(key, result, ex=600)

        return result

    @staticmethod
    def get_last_pay_time(store):
        order = Order.objects.filter(
            store=store, order_type=1).order_by('receive_time')[:1]
        for i in order:
            return i.create_time.strftime("%Y-%m-%d")

    @staticmethod
    def all_store():
        all_store = Store.store_all()
        all_store_list = list()
        for store in all_store:
            all_store_list.append(store.info())

        return {'message': 'ok', 'info': all_store_list}

    @staticmethod
    def sync_store_stock(order, ps_user=None, new=True):

        # [TODO]
        # if new : 新货 car[-],store[+]
        # Sync Car Stock
        # 消息队列

        goods_type = 0
        if new:
            goods_pool = OrderDetail.objects.filter(order_id=order.order_id)
        else:
            goods_pool = RecoverModelDetail.objects.filter(
                order_id=order.order_id)
            goods_type = 1

        try:
            for i in goods_pool:
                # 押金跳过
                if i.goods_id < 0:
                    continue
                store_goods = StoreGoods.objects.get(
                    store=order.store, goods=i.goods,)
                try:
                    car_goods = PeisongCarStock.objects.get(
                        wk=ps_user, goods=i.goods, goods_type=goods_type)
                except Exception as e:
                    if new:
                        # 看实际情况再决定加不加
                        # return {'message': '车上没有此物品!'}
                        raise Exception("配送员车上没有此物品")
                    else:
                        car_goods = PeisongCarStock(
                            wk=ps_user, goods=i.goods, goods_type=goods_type)

                goods_count = i.goods_count
                if not new:
                    goods_count = -(i.goods_count)

                # [TODO] 小于?
                # if new and car_goods.goods_stock < goods_count:
                #     raise Exception("库存不足，补货后再次确认")

                car_goods.goods_stock -= goods_count
                car_goods.save()

                store_goods.goods_stock += goods_count
                store_goods.save()

        except Exception as e:
            app.error(str(e))
            raise e

        return {'message': 'ok'}

    def reply(self):
        method_name = self.action + '_store'
        try:
            method = getattr(self, method_name)
            return method()
        except AttributeError as e:
            app.error(str(e))
            return StoreManager.all_store()


class EmployeeManager(object):
    def __init__(self, action, postdata):
        self.action = action
        self.data = postdata

    def settype_employee(self):
        uid = self.data.get('uid', 0)
        set_type = int(self.data.get('set_type', -1))

        if set_type < 0:
            return {'message': '设置失败'}

        if set_type == 2:
            area_id = int(self.data.get('area_id', 0))
            try:
                area = DeliveryArea.objects.get(id=area_id)
            except Exception as e:
                return {'message': '区域id不存在'}

        else:
            area = None

        try:
            uid = de_base64(txt=uid)
        except Exception as e:
            app.info(str(e))
            return {'message': '用户id错误'}

        try:
            user = User.objects.get(wk=uid)
        except Exception as e:
            app.error(str(e))
            return {'message': '用户id错误'}

        UserManager.set_user_type(user, set_type=set_type, area=area)
        return {'message': 'ok'}

    @staticmethod
    def all_employee():
        all_employee = User.objects.filter(
            Q(user_type=0) | Q(user_type=1) | Q(user_type=2))

        all_employee_list = list()
        for i in all_employee:
            all_employee_list.append(UserManager.get_user_info(i))

        return {'message': 'ok', 'employee_info': all_employee_list}

    def reply(self):
        method_name = self.action + '_employee'
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.error(str(e))
            return {'message': '参数错误'}


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

        if user.user_type <= 3:
            return {'message': '已绑定商家'}

        new_customer = CustomerProfile(wk=user, store=store)
        new_customer.save()

        user.user_type = 3
        user.save()

        return {'message': 'ok'}

    def reply(self):
        store_id = int(self.data.get('store_id', 0))

        try:
            store = Store.objects.get(store_id=store_id)
        except Exception:
            return {"message": '商户id不存在，请联系管理员'}

        return self.bind(store)


class GoodsManager(object):
    """docstring for GoodsManager
    """

    def __init__(self, postdata, action=all):
        self.data = postdata
        self.action = action

    @staticmethod
    def sync_goods_stock(order, new=True):
        goods_pool = PickOrderDetail.objects.filter(order_id=order.order_id)
        try:
            for i in goods_pool:
                if new:
                    # [TODO] 旧货到底去哪?
                    i.goods.goods_stock -= i.goods_count

                try:
                    if new:
                        car_goods = PeisongCarStock.objects.get(
                            wk=order.pick_user, goods=i.goods)
                        car_goods.goods_stock += i.goods_count
                    else:
                        # [TODO] 车上新货回收？
                        car_goods = PeisongCarStock.objects.get(
                            wk=order.pick_user, goods=i.goods, goods_type=1)
                        car_goods.goods_stock -= i.goods_count

                    car_goods.save()
                except Exception as e:
                    if new:
                        car_goods = PeisongCarStock(
                            wk=order.pick_user, goods=i.goods, goods_stock=i.goods_count)
                        car_goods.save()
                    else:
                        raise e

                i.goods.save()
        except Exception as e:
            app.error(str(e))
            return {'message': (str(e))}

        return {'message': 'ok'}

    def add_goods(self):
        goods_name = self.data['name']
        goods_spec = int(self.data.get('spec', 1))
        goods_stock = int(self.data.get('stock', 0))
        goods_img = self.data.get('goods_img', '0')
        is_recover = int(self.data.get('recover', 0))
        goods_type = int(self.data.get('type', 0))

        new_goods = Goods(goods_name=goods_name,
                          goods_spec=goods_spec,
                          goods_stock=goods_stock,
                          is_recover=is_recover,
                          goods_type=goods_type,
                          goods_img=goods_img)
        new_goods.save()

        return {'message': 'ok', 'id': new_goods.goods_id}

    def change_goods(self):
        goods_id = self.data.get('goods_id', 0)
        goods_name = self.data['name']
        goods_spec = int(self.data.get('spec', 1))
        goods_img = self.data.get('goods_img', None)
        try:
            goods = Goods.objects.get(goods_id=goods_id)
            goods.goods_name = goods_name
            goods.goods_spec = goods_spec
            goods.goods_img = goods_img or goods.goods_img
            goods.save()
        except Exception as e:
            app.error(str(e))
            return {'message': '保存失败\n' + str(e)}

        return {'message': 'ok', 'new_info': goods.info()}

    def addstock_goods(self):
        goods_list = self.data.get('goods_list', list())

        for i in goods_list:
            goods_id = int(i.get('goods_id', 0))
            count = int(i.get('count', 0))
            try:
                goods = Goods.objects.get(goods_id=goods_id)
                goods.goods_stock += count
                goods.save()
            except Exception:
                return {'message': '商品id不存在'}

        return {'message': 'ok'}

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
            return {'message': '设置失败'}

    @staticmethod
    def all_goods(is_all=0):
        goods_all = Goods.goods_all(is_all=is_all)

        return_list = list()
        for i in goods_all:
            if i.goods_id < 0:
                continue
            return_list.append(i.info())

        return {'message': 'ok', 'info': return_list}

    @staticmethod
    def get_goods_info(goods_id):
        goods = Goods.objects.get(goods_id=goods_id)
        return goods.info()

    def reply(self):
        method_name = str(self.action) + '_goods'
        is_all = self.data.get('is_all', 0)
        if self.action == 'all':
            return GoodsManager.all_goods(is_all)
        try:
            method = getattr(self, method_name)
            return method()
        except Exception as e:
            app.error(str(e))
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

    def getclear_order(self):
        store = UserManager.get_user_store(self.user).store
        if redis_report.exists(store.store_id):
            print('_redis')
            return eval(redis_report.get(store.store_id))

        return {'message': '暂时还没有提交清账订单'}

    def save_order(self):
        user = self.user
        order_id = OrderManager.gen_order_id()
        store = UserManager.get_user_store(user).store
        area = store.store_area
        remarks = self.data['remarks']

        def save_order_detail(order_id, store):
            """
            [TODO] despoit
            """
            pack_goods = self.data['goods_list']
            order_all_goods = list()
            order_price = 0

            for i in pack_goods:
                goods_id = i['goods_id']
                goods_count = i['goods_count']

                goods = Goods.objects.get(goods_id=goods_id)
                this_goods = StoreGoods.objects.get(
                    goods=goods,
                    store=store
                )
                # delect goods_spec 2018/03/30
                goods_price = this_goods.goods_price

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
            # 押金选项
            if store.has_deposit == 1:
                order_all_goods.append(
                    OrderDetail(
                        order_id=order_id,
                        goods=Goods.objects.get(goods_id=-1),
                        goods_count=1,
                        goods_price=store.store_deposit,
                        total_price=store.store_deposit
                    )
                )
                order_price += store.store_deposit
                store.has_deposit = 0
                store.save()

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
    def set_order_status(order, order_type, pay_from=None, ps_user=None, done_user=None):
        max_cancel_minutes = timedelta(minutes=15)
        order_type = int(order_type)

        # 向上级跳 Refuse
        if order_type != 3 and order.order_type <= order_type:
            return {'message': 'Refuse'}

        # 大于取消时间 Refuse
        if order_type == 3:
            if datetime.now() - order.create_time > max_cancel_minutes:
                return {'message': '大于取消时间'}

            # 如果第一笔有押金的订单取消，恢复押金未付状态！
            if OrderDetail.objects.filter(order_id=order.order_id, 
                                          goods=Goods.objects.get(goods_id=-1)).exists():
                order.store.has_deposit = 1
                order.store.save()

        # 待支付
        if order_type == 1:
            order.receive_time = datetime.now()
            try:
                StoreManager.sync_store_stock(order, ps_user=ps_user)
                order.ps_user = ps_user
            except Exception as e:
                return {'message': str(e)}

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
        order_id = int(self.data.get('order_id', 0))
        try:
            order = Order.objects.get(order_id=order_id)
        except Exception as e:
            return {'message': '订单号错误'}

        order_info = order.info()

        order_goods = order.goods_info()
        return {'message': 'ok',
                'info': order_info,
                'goods': order_goods}

    def cancel_order(self):
        order_id = int(self.data.get('order_id', 0))
        try:
            order = Order.objects.get(order_id=order_id)
        except Exception as e:
            return {'message': '订单号错误'}

        return OrderManager.set_order_status(order, 3)

    def status_order(self):
        status = int(self.data['status'])
        store = UserManager.get_user_store(user=self.user).store
        status_order = list()

        if status > 3:
            return {'message': 'failed'}

        order_list = Order.objects.filter(
            store=store, order_type=status)[:30]

        for i in order_list:
            status_order.append(
                i.info())

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
        self.ps_user = UserManager.get_user_area(user)
        self.area = self.ps_user.area

    @staticmethod
    def get_peisong_order_info(order):
        peisong_detail = {}
        peisong_detail['order_info'] = order.info()
        peisong_detail['goods_info'] = order.goods_info()
        peisong_detail['store_info'] = order.store.info()

        return peisong_detail

    @staticmethod
    def get_pick_order_info(order):
        return {'order_info': order.info(),
                'goods_info': order.goods_info()}

    def get_receive_peisong(self):
        """
        [TODO] Redis

        """
        result = {}
        info = list()

        order_pool = Order.objects.filter(area=self.area, order_type=2)

        for i in order_pool.iterator():
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
            return {'message': '订单号错误'}

        res = OrderManager.set_order_status(order, 1, ps_user=self.ps_user)
        if res['message'] != 'ok':
            return res

        return {'message': 'ok'}

    def get_recover_peisong(self):
        info = list()
        recover_order_pool = RecoverOrder.objects.filter(
            area=self.area, order_type=1)

        for i in recover_order_pool:
            info.append(RecoverManager.get_recover_order_info(i))

        return {'message': 'ok',
                'info': info}

    def set_recover_peisong(self):
        try:
            order_id = int(self.data['order_id'])
        except Exception:
            return {'message': '订单号错误'}

        try:
            order = RecoverOrder.objects.get(order_id=order_id)
        except Exception:
            return {'message': '订单号错误'}

        if order.order_type == 0:
            return {'message': 'ok'}

        res = StoreManager.sync_store_stock(
            order=order, ps_user=self.ps_user, new=False)

        if res['message'] != 'ok':
            return res

        order.ps_user = self.ps_user
        order.order_type = 0
        order.receive_time = datetime.now()
        order.save()

        return {'message': 'ok'}

    @staticmethod
    def order_report_info(order_pool, recover_order_pool):

        pay_order_sum = no_pay_order_sum = month_pay_order_sum = 0
        pay_money_sum = xs_pay_sum = xx_pay_sum = 0

        for i in order_pool.iterator():
            if i.order_type == 0:
                pay_order_sum += 1
                pay_money_sum += i.order_total_price
                if i.pay_from == 0:
                    xx_pay_sum += i.order_total_price
                else:
                    xs_pay_sum += i.order_total_price
            else:
                no_pay_order_sum += 1
                if i.pay_type == 1:
                    month_pay_order_sum += 1

        info = {
            'order_sum': len(order_pool),
            'recover_sum': len(recover_order_pool),
            'pay_order_sum': pay_order_sum,
            'no_pay_order_sum': no_pay_order_sum,
            'month_pay_order_sum': month_pay_order_sum,
            'pay_money_sum': str(pay_money_sum),
            'xs_pay_sum': str(xs_pay_sum),
            'xx_pay_sum': str(xx_pay_sum)
        }

        return info

    @staticmethod
    def stock_report_info(pick_pool):
        pick_order_sum = 0
        recover_order_sum = 0
        goods_sum = list()
        goods_sum_tmp = {}
        order_info = list()

        for i in pick_pool.iterator():
            goods_info = i.goods_info()
            recover_order_sum += i.order_type
            for j in goods_info:
                try:
                    goods_sum_tmp[j['goods_id']] += j['goods_count']
                except Exception:
                    goods_sum_tmp[j['goods_id']] = j.pop('goods_count')

            order_info.append({'info': i.info(), 'goods_info': goods_info})

        for i in goods_sum_tmp:
            goods = Goods.objects.get(goods_id=i)
            goods_sum.append({'goods_id': i,
                              'goods_name': goods.goods_name,
                              'goods_spec': goods.goods_spec,
                              'goods_count': goods_sum_tmp[i]})
        info = {
            'message': 'ok',
            'pick_order_sum': len(pick_pool)-recover_order_sum,
            'recover_order_sum': recover_order_sum,
            'goods_sum': goods_sum,
            'order_info': order_info,
        }

        return info

    def day_order_report(self):
        today = datetime.now()
        day = self.data.get('day', today.day)

        key = str(self.ps_user) + '_' + str(day) + '_day_order_report'
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        order_pool = Order.objects.filter(Q(order_type__lt=2),
                                          Q(ps_user=self.ps_user),
                                          Q(receive_time__month=today.month),
                                          Q(receive_time__day=day) | Q(done_time__day=day))
        recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                         ps_user=self.ps_user,
                                                         receive_time__month=today.month,
                                                         receive_time__day=day)

        info = PeiSongManager.order_report_info(order_pool, recover_order_pool)

        result = {'message': 'ok',
                  'info': info}
        if info['order_sum'] != 0:
            print('new_redis')
            redis_report.set(key, result, ex=600)

        return result

    def month_order_report(self):
        today = datetime.now()
        month = self.data.get('month', today.month)

        if month <= 0 or month > 12:
            month = today.month

        # 如果存在redis缓存 直接返回
        key = str(self.ps_user) + '_' + str(month) + '_month_order_report'
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        order_pool = Order.objects.filter(order_type__lt=3,
                                          ps_user=self.ps_user,
                                          receive_time__month=month)
        recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                         ps_user=self.ps_user,
                                                         receive_time__month=month)

        info = PeiSongManager.order_report_info(order_pool, recover_order_pool)
        result = {'message': 'ok',
                  'info': info}

        if info['order_sum'] != 0:
            print('new_redis')
            redis_report.set(key, result, ex=600)

        return result

    def get_pay_peisong(self):
        result = {}
        info = list()
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
            return {'message': '订单号错误'}

        res = OrderManager.set_order_status(order, 0, pay_from=pay_from)

        if res['message'] != 'ok':
            return res

        return {'message': 'ok'}

    def get_car_stock(self):
        result = list()
        old_info = list()
        goods_pool = PeisongCarStock.objects.filter(wk=self.ps_user)
        for i in goods_pool:
            if i.goods_stock == 0:
                continue
            if i.goods_type == 0:
                result.append(i.info())
            else:
                old_info.append(i.info())

        return {'message': 'ok',
                'info': result,
                'old_info': old_info}

    def get_ps_stock(self):
        # pass
        order_pool = Order.objects.filter(area=self.area, order_type=2)
        result = list()

        info = OrderDetail.objects.raw('select 1 as id,goods_id,sum(goods_count) as goods_count \
                                        from cms_orderdetail where cms_orderdetail.order_id in \
                                        (select order_id from cms_order where order_type={} and area_id={}) \
                                        group by cms_orderdetail.goods_id'.format(2, self.area.id))

        for i in info:
            goods_info = GoodsManager.get_goods_info(i.goods_id)
            if i.goods_id < 0:
                continue
            goods_info['goods_count'] = int(i.goods_count)
            result.append(goods_info)

        return {'message': 'ok',
                'info': result}

    def new_pick(self):
        order_id = OrderManager.gen_order_id()
        pick_user = PeisongProfile.objects.get(wk=self.user)

        def save_pick_detail(order_id, goods_list):
            pickorder_all_goods = list()
            for i in goods_list:
                goods_id = i['goods_id']
                goods_count = i['goods_count']

                try:
                    goods = Goods.objects.get(goods_id=goods_id)
                except Exception as e:
                    app.info(str(e))
                    return {'message': '商品id不存在'}

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
        order_type = self.data.get('order_type', 0)
        PickOrder(order_id=order_id, pick_user=pick_user,
                  order_type=order_type).save()
        info['order_id'] = order_id

        return info

    def get_pick(self):
        # filter all order
        # todo order_type = 1
        info = list()
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
        order_pool = PickOrder.objects.filter(order_status=1)
        info = list()
        for i in order_pool:
            t_info = PeiSongManager.get_pick_order_info(i)
            t_info['user_info'] = {}
            t_info['user_info']['user_name'] = i.pick_user.name
            t_info['user_info']['user_phone'] = i.pick_user.phone
            info.append(t_info)

        return {'message': 'ok',
                'info': info}

    def confirm_pick(self):
        try:
            order_id = int(self.data.get('order_id', 0))
            order = PickOrder.objects.get(order_id=order_id)
        except:
            return {'message': '订单号错误'}

        # todo goods_list
        if order.order_status == 0:
            return {'message': 'failed'}

        if order.order_type == 0:
            info = GoodsManager.sync_goods_stock(order)
        else:
            info = GoodsManager.sync_goods_stock(order, new=False)

        if info['message'] == 'ok':
            order.order_status = 0
            order.confirm_time = datetime.now()
            order.confirm_user = self.user
            order.save()

        return info

    def modify_pick(self):
        order_id = self.data.get('order_id', 0)

        try:
            order = PickOrder.objects.get(order_id=int(order_id))
        except:
            return {'message': '订单号错误'}

        goods_list = self.data['goods_list']

        for i in goods_list:
            try:
                o = PickOrderDetail.objects.get(
                    order_id=order.order_id, goods_id=i['goods_id'])
            except Exception as e:
                return {'message': 'goods_id({}) not exist'.format(i['goods_id'])}
            o.goods_count = i['goods_count']
            o.save()

        order.is_modify = 1
        order.save()
        return dict({'message': 'ok'}, **(PeiSongManager.get_pick_order_info(order)))


class RecoverManager(object):
    """docstring for RecoverManager"""

    def __init__(self, user, **kwargs):
        self.user = user
        self.store_user = UserManager.get_user_store(self.user)
        self.goods_list = kwargs.get('goods_list', None)
        self.order_id = int(kwargs.get('order_id', 0))

    def new_recover_order(self):
        order_id = OrderManager.gen_order_id()

        def save_recover_detail(order_id, goods_list):
            recover_all_goods = list()
            for i in goods_list:
                goods_id = i['goods_id']
                goods_count = i['goods_count']

                try:
                    goods = Goods.objects.get(goods_id=goods_id)
                except Exception as e:
                    app.info(str(e))
                    return {'message': '商品id不存在'}

                recover_all_goods.append(
                    RecoverModelDetail(
                        order_id=order_id,
                        goods=goods,
                        goods_count=goods_count
                    )
                )
            try:
                RecoverModelDetail.objects.bulk_create(recover_all_goods)
            except Exception as e:
                app.error(str(e))
                return {'message': 'failed'}

            return {'message': 'ok'}

        info = save_recover_detail(order_id, self.goods_list)
        if info['message'] != 'ok':
            return info

        RecoverOrder(order_id=order_id, store=self.store_user.store,
                     user=self.store_user, area=self.store_user.store.store_area).save()
        info['order_id'] = order_id

        return info

    @staticmethod
    def get_recover_order_info(order):
        return {'order_info': order.info(),
                'goods_lnfo': order.goods_info()}

    def cancel_recover_order(self):
        order_id = self.order_id

        try:
            order = RecoverOrder.objects.get(order_id=order_id)
        except:
            return {'message': '订单号错误'}

        if order.order_type == 0:
            return {'message': 'failed'}

        max_cancel_minutes = timedelta(minutes=30)
        if datetime.now() - order.create_time > max_cancel_minutes:
            return {'message': '大于取消时间'}
        else:
            order.order_type = 2
            order.save()
            return {'message': 'ok'}

    def status_recover_order(self):
        try:
            order_pool = RecoverOrder.objects.filter(
                store=self.store_user.store, order_type=1)
        except:
            return {'message': '订单号错误'}

        info = [RecoverManager.get_recover_order_info(i) for i in order_pool]
        return {'message': 'ok',
                'info': info}


class BoosReport(object):
    """docstring for BoosReport"""

    def __init__(self, postdata=None, user=None):
        self.data = postdata
        self.today = datetime.now()

    def day_order_report(self):
        day = self.data.get('day', self.today.day)
        ps_user_uid = self.data.get('uid', None)
        ps_user = None
        if ps_user_uid:
            try:
                ps_user = de_base64(ps_user_uid)
                ps_user = PeisongProfile.objects.get(wk=ps_user)
            except Exception:
                ps_user = None

        # Redis
        key = str(ps_user) + '_' + str(day) + '_day_order_report'
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        if ps_user:
            order_pool = Order.objects.filter(Q(order_type__lt=2),
                                              Q(ps_user=ps_user),
                                              Q(receive_time__month=self.today.month),
                                              Q(receive_time__day=day) | Q(done_time__day=day))
            recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                             ps_user=ps_user,
                                                             receive_time__month=self.today.month,
                                                             receive_time__day=day)
        else:
            order_pool = Order.objects.filter(Q(order_type__lt=2),
                                              Q(receive_time__month=self.today.month),
                                              Q(receive_time__day=day) | Q(done_time__day=day))
            recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                             receive_time__month=self.today.month,
                                                             receive_time__day=day)

        info = PeiSongManager.order_report_info(order_pool, recover_order_pool)
        result = {'message': 'ok',
                  'info': info}
        if info['order_sum'] != 0:
            redis_report.set(key, result, ex=600)

        return result

    def month_order_report(self):
        month = self.data.get('month', self.today.month)

        if month <= 0 or month > 12:
            month = today.month

        ps_user_uid = self.data.get('uid', None)
        ps_user = None
        if ps_user_uid:
            try:
                ps_user = de_base64(ps_user_uid)
                ps_user = PeisongProfile.objects.get(wk=ps_user)
            except Exception:
                ps_user = None
        # Redis
        key = str(ps_user) + '_' + str(month) + '_day_order_report'
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        if ps_user:
            order_pool = Order.objects.filter(order_type__lt=2,
                                              ps_user=ps_user,
                                              receive_time__month=month)
            recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                             ps_user=ps_user,
                                                             receive_time__month=month)
        else:
            order_pool = Order.objects.filter(order_type__lt=2,
                                              receive_time__month=month)
            recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                             receive_time__month=month)

        info = PeiSongManager.order_report_info(order_pool, recover_order_pool)
        result = {'message': 'ok',
                  'info': info}
        if info['order_sum'] != 0:
            redis_report.set(key, result, ex=600)

        return result

    def day_stock_report(self):
        day = self.data.get('day', self.today.day)
        ps_user_uid = self.data.get('uid', None)
        ps_user = None
        if ps_user_uid:
            try:
                ps_user = de_base64(ps_user_uid)
                ps_user = PeisongProfile.objects.get(wk=ps_user)
            except Exception:
                ps_user = None

        # 如果存在redis缓存 直接返回
        key = str(ps_user) + '_' + str(day) + '_day_stock_report'
        if redis_report.exists(key):
            return eval(redis_report.get(key))

        if ps_user:
            pick_pool = PickOrder.objects.filter(order_status=0,
                                                 pick_user=ps_user,
                                                 confirm_time__month=self.today.month,
                                                 confirm_time__day=day)
        else:
            pick_pool = PickOrder.objects.filter(order_status=0,
                                                 confirm_time__month=self.today.month,
                                                 confirm_time__day=day)

        info = PeiSongManager.stock_report_info(pick_pool)
        if len(info['goods_sum']) != 0:
            redis_report.set(key, info, ex=600)
            print('new_redis')
        return info

    def month_stock_report(self):
        month = self.data.get('month', self.today.month)
        if month <= 0 or month > 12:
            month = today.month

        ps_user_uid = self.data.get('uid', None)
        ps_user = None

        if ps_user_uid:
            try:
                ps_user = de_base64(ps_user_uid)
                ps_user = PeisongProfile.objects.get(wk=ps_user)
            except Exception as e:
                ps_user = None

        # 如果存在redis缓存 直接返回
        key = str(ps_user) + '_' + str(month) + '_month_stock_report'
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        if ps_user:
            pick_pool = PickOrder.objects.filter(order_status=0,
                                                 pick_user=ps_user,
                                                 confirm_time__month=month)
        else:
            pick_pool = PickOrder.objects.filter(order_status=0,
                                                 confirm_time__month=month)

        info = PeiSongManager.stock_report_info(pick_pool)
        if len(info['goods_sum']) != 0:
            redis_report.set(key, info, ex=600)
            print('new_redis')
        return info

    def month_store_report(self):
        month = self.data.get('month', self.today.month)
        store_id = self.data.get('store_id', None)

        if month <= 0 or month > 12:
            month = today.month

        if store_id:
            try:
                store = Store.objects.get(store_id=store_id)
            except Exception as e:
                store = None

        key = str(store_id) + '_' + str(month) + '_month_store_report'
        # Redis
        if redis_report.exists(key):
            print('_redis')
            return eval(redis_report.get(key))

        if store:
            order_pool = Order.objects.filter(order_type__lt=2,
                                              store=store, receive_time__month=month)
            recover_order_pool = RecoverOrder.objects.filter(order_type__lt=1,
                                                             store=store, receive_time__month=month)
        else:
            order_pool = Order.objects.filter(
                order_type__lt=2, create_time__month=month)
            recover_order_pool = RecoverOrder.objects.filter(
                order_type__lt=1, create_time__month=month)

        info = StoreManager.store_report_info(
            order_pool=order_pool, recover_order_pool=recover_order_pool)
        result = {'message': 'ok', 'info': info}

        if info['order_sum'] != 0:
            print('new_redis')
            redis_report.set(key, result, ex=600)

        return result


class ClearAccount(object):
    """docstring for ClearAccount"""

    def __init__(self, postdata=None, key=None):
        self.key = key
        self.data = postdata

    def getmonth_clear(self):
        info = list()
        store_pool = Store.objects.filter(store_pay_type=1)
        for i in store_pool:
            info.append({'stroe_id': i.store_id,
                         'store_name': i.store_name,
                         'is_clear': redis_report.exists(i.store_id),
                         'last_pay_time': StoreManager.get_last_pay_time(i)})

        return {'message': 'ok',
                'info': info}

    def new_clear(self):
        try:
            store_id = int(self.data.get('store_id', 0))
            store = Store.objects.get(store_id=store_id)
        except Exception as e:
            return {'message': '商户id不存在'}

        try:
            b_time = datetime.strptime(self.data.get('b_time'), '%Y-%m-%d')
            e_time = datetime.strptime(self.data.get('e_time'), '%Y-%m-%d')
        except Exception:
            if redis_report.get(store_id):
                print('_redis')
                return eval(redis_report.get(store_id))
            else:
                return {'message': '时间错误'}

        order_pool = Order.objects.filter(
            Q(order_type=1, receive_time__gte=b_time, receive_time__lt=e_time))

        info = list()
        total_price = 0
        for i in order_pool:
            t_info = i.info()
            total_price += i.order_total_price
            info.append({'order_info': t_info, 'goods_info': i.goods_info()})

        result = {'message': 'ok',
                  'total_price': str(total_price),
                  'info': info}

        redis_report.set(store_id, result, ex=86400)
        return result

    def confirm_clear(self):
        try:
            store_id = int(self.data.get('store_id', 0))
            store = Store.objects.get(store_id=store_id)
        except Exception:
            return {'message': '商户id不存在'}

        if redis_report.exists(store_id):
            data = eval(redis_report.get(store_id))
        else:
            return {'message': 'clear order expired'}
        
        for i in data['info']:
            try:
                order = Order.objects.get(order_id=i['order_info']['order_id'])
            except Exception as e:
                app.error(str(e))
                return {'message': 'failed'}
            info = OrderManager.set_order_status(
                order=order, order_type=0, pay_from=2)
            if info['message'] != 'ok':
                return info
        redis_report.delete(store_id)
        return info

    def detail_clear():
        # [TODO] return all clear detail and confirm user
        pass


class Ad:
    def __init__(self, postdata=None):
        self.data = postdata

    def setb_ad(self):
        img_list = self.data['img_list']
        for i in img_list:
            AdBanner(b_img=i).save()

        Ad.flush_redis()
        return {'message': 'ok', 'info': AdBanner.all()}

    def setc_ad(self):
        c_title = self.data.get('title', '')
        c_content = self.data.get('content', '')
        c_img = self.data.get('img', '')

        if len(c_title) == 0 or len(c_content) == 0:
            return {'message': '标题或内容不能为空'}

        AdContent(c_title=c_title, c_content=c_content, c_img=c_img).save()

        Ad.flush_redis()
        return {'message': 'ok', 'info': AdContent.all()}

    def delc_ad(self):
        id = self.data.get('id', 0)
        try:
            ad = AdContent.objects.get(id=int(id))
        except:
            return {'message': 'id不存在'}

        ad.delete()
        Ad.flush_redis()
        return {'message': 'ok'}

    def delb_ad(self):
        id = self.data.get('id', 0)
        try:
            ad = AdBanner.objects.get(id=int(id))
        except:
            return {'message': 'id不存在'}

        ad.delete()
        Ad.flush_redis()
        return {'message': 'ok'}

    @staticmethod
    def get():
        if redis_report.exists('ad:key'):
            return eval(redis_report.get('ad:key'))
        else:
            Ad.flush_redis()
            return {'message': 'ok',
                    'banner': AdBanner.all(),
                    'content': AdContent.all()}

    @staticmethod
    def flush_redis():
        try:
            info = {'message': 'ok',
                'banner': AdBanner.all(),
                'content': AdContent.all()}
            redis_report.set('ad:key',info)
        except Exception as e:
            app.error(str(e))