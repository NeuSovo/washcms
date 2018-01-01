from django.test import TestCase
from cms.models import User
from random import randint
# Create your tests here.

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
    def test_creat_user(self):
        for i in range(100):
            creat(i,randint(0,3))



