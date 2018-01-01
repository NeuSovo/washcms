from django.db import models

# Create your models here.
# class UserProfile


class User(models.Model):
    wk = models.CharField(max_length=100, blank=True, primary_key=True)
    is_admin = models.IntegerField(default=0)
    is_courier = models.IntegerField(default=0)
    is_customer = models.IntegerField(default=0)

    def all_admin(self):
        return User.objects.all().filter(is_admin=1)

    def all_courier(self):
        return User.objects.all().filter(is_courier=1)

    def all_customer(self):
        return User.objects.all().filter(is_customer=1)

    def save(self):
        super().save()
        Profile(wk=self).save()


class Profile(models.Model):
    wk = models.OneToOneField(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, default='no register')
    
    # pass


class Session(models.Model):
    session_key = models.CharField(max_length=100, primary_key=True)
    session_data = models.CharField(max_length=100, unique=True)
    we_ss_key = models.CharField(max_length=100)
    expire_date = models.DateTimeField()


class ClassName(object):
    """docstring for ClassName"""
    pass

class CodeRecord(models.Model):
    code_key = models.IntegerField(primary_key=True)
    code_name = models.CharField(max_length=100,default='not defined')
    code_count = models.IntegerField(default=0)
