from django.db import models

# Create your models here.
# class UserProfile


class User(models.Model):

    type_level = (
        (0, u'管理员'),
        (1, u'配送员'),
        (2, u'库管'),
        (3, u'顾客'),
        (4, u'未注册')
    )
    wk = models.CharField(max_length=100, unique=True, primary_key=True)
    user_type = models.IntegerField(
        default=4, choices=type_level, verbose_name='用户身份')
    nick_name = models.CharField(max_length=100, default='nick_name')
    avatar_links = models.CharField(
        max_length=150, default='https://pic3.zhimg.com/aadd7b895_s.jpg')
    reg_date = models.DateTimeField(auto_now_add=True)

    @staticmethod
    def all_admin():
        return User.objects.all().filter(user_type=0)

    @staticmethod
    def all_courier():
        return User.objects.all().filter(user_type=1)

    @staticmethod
    def all_customer():
        return User.objects.all().filter(user_type=3)

    @staticmethod
    def User_all():
        return User.objects.all()

    def __len__(self):
        return len(User.User_all())

    def save(self):
        super().save()


class DeliveryArea(models.Model):
    area_name = models.CharField(max_length=150)

    @staticmethod
    def Area_all():
        return DeliveryArea.objects.all()

    def __len__(self):
        return len(DeliveryArea.Area_all())


class Store(models.Model):
    pay_type_level = (
        (0, '日结'),
        (1, '月结'),
    )
    area_level = []
    for i in DeliveryArea.Area_all():
        area_level.append([i.id, i.area_name])

    store_id = models.AutoField(primary_key=True)
    store_name = models.CharField(max_length=155, default=0)
    store_phone = models.IntegerField(default=0)
    store_addr = models.TextField(default=0)
    store_area = models.IntegerField(default=0, choices=area_level)
    store_pay_type = models.IntegerField(default=0, choices=pay_type_level)
    store_deposit = models.IntegerField(default=0)

    @staticmethod
    def Store_all():
        return Store.objects.all()

    def __len__(self):
        return len(Store.Store_all())


class CustomerProfile(models.Model):

    wk = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    store_id = models.IntegerField(default=0)


class CourierProfile(models.Model):

    wk = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    area_id = models.IntegerField(default=-1)


class Goods(models.Model):
    pass


class Session(models.Model):
    session_key = models.CharField(max_length=100, primary_key=True)
    session_data = models.CharField(max_length=100, unique=True)
    we_ss_key = models.CharField(max_length=100)
    expire_date = models.DateTimeField()


class CodeRecord(models.Model):
    code_key = models.IntegerField(primary_key=True)
    code_name = models.CharField(max_length=100, default='not defined')
    code_count = models.IntegerField(default=0)
