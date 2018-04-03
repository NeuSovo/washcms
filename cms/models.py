import time
from django.db import models
from django.utils import timezone
from datetime import datetime,timedelta
# Create your models here.
# class UserProfile


class User(models.Model):

    class Meta:
        verbose_name = "所有用户"
        verbose_name_plural = "Users"
        ordering = ['-last_login']

    type_level = (
        (0, u'管理员'),
        (1, u'库管'),
        (2, u'配送员'),
        (3, u'顾客'),
        (4, u'未注册')
    )
    wk = models.CharField(
            max_length=100,
            null=False,
            primary_key=True
        )
    user_type = models.IntegerField(
                    default=4,
                    choices=type_level,
                    verbose_name='用户身份'
                )
    nick_name = models.CharField(
                    max_length=100,
                    default='nick_name'
                )
    avatar_links = models.CharField(
                        max_length=150,
                        default='https://pic3.zhimg.com/aadd7b895_s.jpg'
                    )
    reg_date = models.DateTimeField(
                   auto_now_add=True
                )
    last_login = models.DateTimeField(default=timezone.now)

    @staticmethod
    def all_admin():
        return User.objects.all().filter(user_type=0)

    @staticmethod
    def all_courier():
        return User.objects.all().filter(user_type=2)

    @staticmethod
    def all_customer():
        return User.objects.all().filter(user_type=3)

    @staticmethod
    def user_all():
        return User.objects.all()

    def __len__(self):
        return len(User.user_all())

    def __str__(self):
        return '%s : %s' % (self.nick_name, self.type_level[self.user_type])


class DeliveryArea(models.Model):

    class Meta:
        verbose_name = "配送区域"
        verbose_name_plural = "DeliveryArea"

    area_name = models.CharField(max_length=150)

    @staticmethod
    def area_all():
        return DeliveryArea.objects.all()

    def __len__(self):
        return len(DeliveryArea.area_all())


class Store(models.Model):
    class Meta:
        verbose_name = "商户"
        verbose_name_plural = "Store"

    pay_type_level = (
        (0, '日结'),
        (1, '月结'),
    )
    area_level = []
    # for i in DeliveryArea.area_all():
    #     area_level.append([i.id, i.area_name])

    store_id = models.IntegerField(
                    primary_key=True
                )
    store_name = models.CharField(
                    max_length=155,
                    default=0
                )
    store_phone = models.BigIntegerField(
                    default=0
                )
    store_addr = models.CharField(
                    max_length=150,
                    default='无'
                )
    store_area = models.ForeignKey(
                    DeliveryArea,
                    on_delete=models.CASCADE
                )
    store_pay_type = models.IntegerField(
                    default=0,
                    choices=pay_type_level
                )
    store_deposit = models.IntegerField(
                    default=0
                )

    @staticmethod
    def store_all():
        return Store.objects.all()

    def __len__(self):
        return len(Store.store_all())


class CustomerProfile(models.Model):

    class Meta:
        verbose_name = "顾客资料"
        verbose_name_plural = "CustomerProfiles"

    wk = models.OneToOneField(
                User,
                on_delete=models.CASCADE,
                primary_key=True
            )
    store = models.ForeignKey(
                Store,
                on_delete=models.CASCADE
            )


class PeisongProfile(models.Model):

    class Meta:
        verbose_name = "配送员资料"
        verbose_name_plural = "PeisongProfile"

    wk = models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            primary_key=True
        )
    area = models.ForeignKey(
            DeliveryArea,
            on_delete=models.CASCADE
        )
    name = models.CharField(
            default='peisong_name',
            max_length=50
        )
    phone = models.BigIntegerField(
            default=0
        )

    def __str__(self):
        return '{},{}'.format(self.name,self.area_id)


class Goods(models.Model):

    class Meta:
        verbose_name = "商品列表"
        verbose_name_plural = "Goodss"

    recover_level = (
        (0, '回收'),
        (1, '不回收')
    )
    goods_id = models.AutoField(
                    primary_key=True
                )
    goods_name = models.CharField(
                    max_length=155,
                    default='not name'
                )
    goods_spec = models.IntegerField(
                    default=0
                )
    goods_stock = models.IntegerField(
                    default=0
                )
    is_recover = models.IntegerField(
                    default=0,
                    choices=recover_level
                )

    @staticmethod
    def goods_all():
        return Goods.objects.all()


class PeisongCarStock(models.Model):
    goods_type_choice = (
        (0, '新货'),
        (1, '旧货')
        )

    class Meta:
        verbose_name = "配送员车上货物"
        verbose_name_plural = "PeisongCarStocks"

    wk = models.ForeignKey(
            PeisongProfile,
            on_delete=models.CASCADE
        )
    goods = models.ForeignKey(
            Goods,
            on_delete=models.CASCADE
        )
    goods_stock = models.IntegerField(
            default=0
        )
    goods_type = models.IntegerField(
            default=0,
            choices=goods_type_choice 
        )


class StoreGoods(models.Model):

    class Meta:
        verbose_name = "商户货物"
        verbose_name_plural = "StoreGoodss"

    store_level = []
    goods_level = []
    # for i in Store.store_all():
    #     store_level.append([i.store_id,i.store_name])

    # for i in Goods.goods_all():
    #     goods_level.append([i.goods_id, i.goods_name])
    store = models.ForeignKey(
                    Store,
                    on_delete=models.CASCADE
                )
    goods = models.ForeignKey(
                    Goods,
                    on_delete=models.CASCADE
                )
    goods_stock = models.IntegerField(
                    default=0
                )
    goods_price = models.DecimalField(
                    max_digits=8,
                    decimal_places=3
                )
    # goods_name = models.CharField(
    #                 max_length=155
    #             )
    # goods_spec = models.IntegerField(
    #                 default=1
    #             )


class Order(models.Model):

    class Meta:
        verbose_name = "商户订单"
        verbose_name_plural = "Orders"
        ordering = ['-create_time']

    def get_order_detail(self):
        return OrderDetail.objects.filter(order_id=self.order_id)

    def info(self):
        return {
            'order_id': str(self.order_id),
            'create_time': str(self.create_time),
            'create_timestamp': time.mktime(self.create_time.timetuple()),
            'order_type': self.order_type,
            'pay_type': self.pay_type,
            'order_total_price': str(self.order_total_price),
            'receive_time': str(self.receive_time),
            'pay_from': self.pay_from,
            'remarks': self.order_remarks,
            'done_time': str(self.done_time)
        }

    def goods_info(self):
        result = []
        goods = OrderDetail.objects.filter(order_id=self.order_id)

        for i in goods:
            result.append({'goods_id': i.goods.goods_id,
                           'goods_name': i.goods.goods_name,
                           'goods_spec': i.goods.goods_spec,
                           'goods_count': i.goods_count,
                           'total_price': str(i.total_price)})

        return result

    pay_type_level = (
        (0, '日结'),
        (1, '月结')
        )
    order_type_level = (
        (0, '已完成'),
        (1, '待支付'),
        (2, '待送达'),
        (3, '已取消')
        )
    pay_from_level = (
        (0, '现金'),
        (1, '微信'),
        (2, '月结'),
        (3, '未支付')
    )

    order_id = models.BigIntegerField(
                    primary_key=True
                )
    create_time = models.DateTimeField(
                    auto_now_add=True
                )
    store = models.ForeignKey(
                    Store,
                    on_delete=models.CASCADE
                )
    user = models.ForeignKey(
                    CustomerProfile,
                    on_delete=models.CASCADE
                )
    area = models.ForeignKey(
                    DeliveryArea,
                    on_delete=models.CASCADE
                )
    ps_user = models.ForeignKey(
                    PeisongProfile,
                    on_delete=models.CASCADE,
                    null=True,
                    blank=True
                )
    order_type = models.IntegerField(
                choices=order_type_level,
                default=2
                )
    receive_time = models.DateTimeField(
                null=True,
                blank=True
                )
    pay_type = models.IntegerField(
                choices=pay_type_level,  
                default=0
                )
    pay_from = models.IntegerField(
                choices=pay_from_level,
                default=3
                )
    order_total_price = models.DecimalField(
                    max_digits=8,
                    decimal_places=3
                )
    order_remarks = models.CharField(
                    max_length=155
                )
    done_time = models.DateTimeField(
                    null=True,
                    blank=True
                )


class OrderDetail(models.Model):

    class Meta:
        verbose_name = "订单详情"
        verbose_name_plural = "OrderDetails"

    order_id = models.BigIntegerField(null=True)

    goods = models.ForeignKey(
                Goods,
                on_delete=models.CASCADE
            )
    goods_count = models.IntegerField()
    goods_price = models.DecimalField(
                    max_digits=8,
                    decimal_places=3
                )
    total_price = models.DecimalField(
                    max_digits=8,
                    decimal_places=3
                )


class PickOrder(models.Model):

    class Meta:
        verbose_name = "领货订单"
        verbose_name_plural = "PickOrders"
        ordering = ['-create_time'] 

    def get_order_detail(self):
        return PickOrderDetail.objects.filter(order_id=self.order_id)    

    modify_level = (
        (0, '未被修改'),
        (1, '被修改')
        )
    order_type_level = (
        (-1, '取消'),
        (0, '已确认'),
        (1, '未确认')
        )

    order_id = models.BigIntegerField(
                    primary_key=True
                )
    order_type = models.IntegerField(
                choices=order_type_level,
                default=1
                )
    create_time = models.DateTimeField(
                    auto_now_add=True
                )
    pick_user = models.ForeignKey(
                    PeisongProfile,
                    on_delete=models.CASCADE
                )
    confirm_user = models.ForeignKey(
                    User,
                    null=True,
                    on_delete=models.CASCADE
                )
    confirm_time = models.DateTimeField(
                    null=True,
                    blank=True
                )
    is_modify = models.IntegerField(
                default=0
                )
    

class PickOrderDetail(models.Model):

    class Meta:
        verbose_name = "PickOrderDetail"
        verbose_name_plural = "PickOrderDetails"

    def __str__(self):
        pass

    order_id = models.BigIntegerField(null=True)
    goods = models.ForeignKey(
            Goods,
            on_delete=models.CASCADE 
        )
    goods_count = models.IntegerField()


class RecoverOrder(models.Model):
    order_type_level = (
        (0, '已完成'),
        (1, '待取货'),
        (2, '已取消')
        )
    class Meta:
        verbose_name = "RecoverOrder"
        verbose_name_plural = "RecoverOrders"

    order_id = models.BigIntegerField(
                    primary_key=True
                )
    create_time = models.DateTimeField(
                    auto_now_add=True
                )
    store = models.ForeignKey(
                    Store,
                    on_delete=models.CASCADE
                )
    user = models.ForeignKey(
                    CustomerProfile,
                    on_delete=models.CASCADE
                )
    area = models.ForeignKey(
                    DeliveryArea,
                    on_delete=models.CASCADE
                )
    ps_user = models.ForeignKey(
                    PeisongProfile,
                    on_delete=models.CASCADE,
                    null=True
                )
    order_type = models.IntegerField(
                choices=order_type_level,
                default=1
                )
    receive_time = models.DateTimeField(
                null=True,
                blank=True
                )

    def get_order_detail(self):
        return RecoverModelDetail.objects.filter(order_id=self.order_id)    
 
class RecoverModelDetail(models.Model):

    class Meta:
        verbose_name = "RecoverModelDetail"
        verbose_name_plural = "RecoverModelDetails"
    
    order_id = models.BigIntegerField(
                    null=True
                )
    goods = models.ForeignKey(
            Goods,
            on_delete=models.CASCADE 
        )

    goods_count = models.IntegerField()


class Session(models.Model):
    session_key = models.CharField(
                    max_length=100,
                    primary_key=True
                )
    session_data = models.CharField(
                    max_length=100,
                    unique=True
                )
    we_ss_key = models.CharField(
                    max_length=100,
                    default='None',
                )
    expire_date = models.DateTimeField()


class CodeRecord(models.Model):
    code_key = models.IntegerField(
                primary_key=True
            )
    code_name = models.CharField(
                max_length=100, 
                default='not defined',
            )
    code_count = models.IntegerField(
                default=0
            )

