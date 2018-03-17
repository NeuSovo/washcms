from django.db import models
from django.utils import timezone
from datetime import datetime,timedelta
# Create your models here.
# class UserProfile


class User(models.Model):

    type_level = (
        (0, u'管理员'),
        (1, u'库管'),
        (2, u'配送员'),
        (3, u'顾客'),
        (4, u'未注册')
    )
    wk = models.CharField(
            max_length=100,
            unique=True,
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

    class Meta:
        ordering = ['-last_login']


class DeliveryArea(models.Model):
    area_name = models.CharField(max_length=150)

    @staticmethod
    def area_all():
        return DeliveryArea.objects.all()

    def __len__(self):
        return len(DeliveryArea.area_all())


class Store(models.Model):
    pay_type_level = (
        (0, '日结'),
        (1, '月结'),
    )
    area_level = []
    for i in DeliveryArea.area_all():
        area_level.append([i.id, i.area_name])

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
    store_area = models.IntegerField(
                    default=0,
                    choices=area_level
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

    wk = models.OneToOneField(
                User,
                on_delete=models.CASCADE,
                primary_key=True
            )
    store_id = models.IntegerField(
                default=-1
            )


class CourierProfile(models.Model):

    wk = models.OneToOneField(
            User,
            on_delete=models.CASCADE,
            primary_key=True
        )
    area_id = models.IntegerField(
            default=-1
        )
    name = models.CharField(
            default='peisong_name',
            max_length=50
        )
    phone = models.BigIntegerField(
            default=0
        )


class Goods(models.Model):
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


class StoreGoods(models.Model):
    store_level = []
    goods_level = []
    for i in Store.store_all():
        store_level.append([i.store_id,i.store_name])

    for i in Goods.goods_all():
        goods_level.append([i.goods_id, i.goods_name])
    store_id = models.IntegerField(
                    choices=store_level,
                    null=False,
                    blank=True
                )
    goods_id = models.IntegerField(
                    choices=goods_level,
                    null=False,
                    blank=True
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
    pay_type_level = (
        (0, '日结'),
        (1, '月结')
        )
    order_type_level = (
        (0,'已完成'),
        (1,'待支付'),
        (2,'待送达'),
        (3,'已取消')
        )
    pay_from_level = (
        (0, '现金'),
        (1, '微信'),
        (2, '月结'),
        (3, '未支付')
    )

    store_level = []
    area_level = []
    for i in Store.store_all():
        store_level.append([i.store_id,i.store_name])

    order_id = models.BigIntegerField(
                    primary_key=True
                )
    create_time = models.DateTimeField(
                    auto_now_add=True
                )
    store_id = models.IntegerField(
                    choices=store_level,
                    blank=False
                )
    user_id = models.CharField(
                    max_length=155
                )
    area_id = models.IntegerField(
                    blank=False
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
    class Meta:
        ordering = ['-create_time']


class OrderDetail(models.Model):
    order_id = models.BigIntegerField()
    goods_id = models.IntegerField()
    goods_count = models.IntegerField()
    goods_price = models.DecimalField(
                    max_digits=8,
                    decimal_places=3
                )
    total_price = models.DecimalField(
                    max_digits=8,
                    decimal_places=3
                )


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
    expire_date = models.DateTimeField(
              )


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

