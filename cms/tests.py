from django.test import TestCase,Client
from cms.models import User,Session
from cms.handle import WechatSdk
from django.conf import settings
import random
import time
import json
from hashlib import sha256, md5
from datetime import datetime,timedelta
# Create your tests here.

class AdminUserTestCase(TestCase):
    wckey = ''
    client = Client()
    TOKEN = 'eq021n!3'

    def setUp(self):
        settings.DEBUG = False
        wk = random.randint(10000,20000)
        self.wckey = WechatSdk.gen_hash()
        User.objects.create(wk=wk,user_type=0)
        Session.objects.create(session_key=wk,session_data=self.wckey)

    def test_normal_login_user(self):
        now_time = time.time()

        to_check_str = str(self.TOKEN) + str(now_time)
        to_check_str = to_check_str.encode('utf-8')

        m = md5()
        m.update(to_check_str)

        cc_str = m.hexdigest()

        json_data = {'base_req':{'wckey':self.wckey},'sign':cc_str,'time':now_time }
        res = self.client.post('/auth/login',json.dumps(json_data), content_type="application/json")
        self.assertEqual(res.status_code,200)

        print (res.json())

    def test_failed_token_login(self):
        json_data = {'base_req':{'wckey':self.wckey},'sign':'cc_str','time':time.time()}
        res = self.client.post('/auth/login',json.dumps(json_data), content_type="application/json")

        self.assertEqual(res.json()['code'],1005)

    def test_expire_time_login(self):
        now_time = int(time.time())-int(6)

        to_check_str = str(self.TOKEN) + str(now_time)
        to_check_str = to_check_str.encode('utf-8')

        m = md5()
        m.update(to_check_str)

        cc_str = m.hexdigest()

        json_data = {'base_req':{'wckey':self.wckey},'sign':cc_str,'time':now_time}
        res = self.client.post('/auth/login',json.dumps(json_data), content_type="application/json")

        self.assertEqual(res.json()['code'],1005)

    def test_store(self):
        json_data = {'base_req':{'wckey':self.wckey},
