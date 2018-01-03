from django.test import TestCase,Client
from cms.models import User
from django.conf import settings
import time
# Create your tests here.
c = Client()
def creat(wk,utype):
    u = User(wk=wk)
    if utype==0:
        u.is_admin = 1
    if utype==1:
        u.is_courier = 1
    if utype==2:
        u.is_customer = 1

    u.save()

class UserTestCase(TestCase):
    def setUp(self):
        settings.DEBUG = True
        res = c.get('/auth/reg',{'code':0})
        print (res.json())
    def test_creat_user(self):
        for i in range(0,101):
            
            # 测试注册
            res = c.get('/auth/reg',{'code':i})
            print (res.json())

            # 测试登陆
            res = c.get('/auth/login',{'sign':i,'time':int(time.time())})
            print (res.json())
