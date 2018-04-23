import random
import time
import json
from cms.models import User
from django.test import TestCase,Client
# Create your tests here.

class CompleteTest(TestCase):
    """docstring for CompleteTest"""

    def setUp(self):
        self.wckey =  'cdddd0bbd854a21ac7afdbd47b66c191483e6c9fcdf9cf2d7e115c8ad8ba0075'
        User.objects.create(wk='debug_admin',user_type=0)

    def test_Complete(self):
        now_time = time.time()

        to_check_str = str(self.TOKEN) + str(now_time)
        to_check_str = to_check_str.encode('utf-8')

        m = md5()
        m.update(to_check_str)

        cc_str = m.hexdigest()

        json_data = {'base_req':{'wckey':self.wckey},'sign':cc_str,'time':now_time }
        res = self.client.post('/auth/login',json.dumps(json_data), content_type="application/json")
        self.assertEqual(res.json()['user_type'], 0)
        
