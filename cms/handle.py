# -*- coding: utf-8 -*-
import os
import json
import time
import base64
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
                print("loginfo : {}:{}".format(func.__name__, body))
            except:
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

            if user_type == -1 or user.user_type == user_type:
                return func(request)
            else:
                return parse_info({'message': 'user_type faild'})

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

    def gen_hash(self):
        """
        gen_hash as session data.
        The repetition should be a very small probability event, 
        and from a statistical point of view, the probability is zero.
        Return a string of length 64.
        """
        return (sha256(os.urandom(24)).hexdigest())

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

        sess = self.gen_hash()

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
        sess = self.gen_hash()

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

    def gen_base64(self, txt):
        tmp = base64.b64encode(str(txt).encode('utf-8'))
        return str(tmp, 'utf-8')

    def get_info(self, user):
        name = user.nick_name
        avatar_links = user.avatar_links

        return {'name': name,
                'avatar_links': avatar_links,
                'qrcod': self.gen_base64(user.wk)}  # 'https://pan.baidu.com/share/qrcode?url=' + self.gen_base64(user.wk)}

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
        '''
            post name
        '''
        new_area = DeliveryArea(area_name=self.data['name'])
        new_area.save()

        return {'message': 'ok', 'id': new_area.id}

    def del_area(self):
        '''
            post id
        '''
        try:
            DeliveryArea.objects.get(id=self.data['id']).delete()
        except:
            return {'message': 'delete faild'}

        return {'message': 'ok'}

    def change_area(self):
        '''
             post id,new_name
        '''
        area = DeliveryArea.objects.get(id=self.data['id'])
        area.area_name = self.data['name']
        area.save()
        return {'message': 'ok', 'new_name': area.area_name}

    @staticmethod
    def all_area():
        '''
            None
        '''
        allarea = DeliveryArea.objects.all()
        all_area_list = []
        for _i in allarea:
            all_area_list.append({'id': _i.id,
                                  'name': _i.area_name})

        return {'message': 'ok',
                'info': all_area_list}

    def reply(self):
        user = get_user(self.wckey)

        if self.action == 'add':
            return self.add_area()
        elif self.action == 'change':
            return self.change_area()
        elif self.action == 'del':
            return self.del_area()
        else:
            return AreaManager.all_area()

        return info


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
            return {'message': 'delete faild'}

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
            return {'message': 'faild'}

    @staticmethod
    def all_store():
        all_store = Store.objects.all()
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

    def reply(self):
        user = get_user(self.wckey)

        if self.action == 'add':
            return self.add_store()
        elif self.action == 'change':
            return self.change_store()
        elif self.action == 'del':
            return self.del_store()
        else:
            return StoreManager.all_store()

    def __str__(self):
        return len(self.postdata)


class SetUserManager(object):
    def __init__(self, postdata):
        self.data = postdata

    def set_user(self, uid, set_type, area_id=-1):
        try:
            uid = base64.b64decode(uid.encode('utf-8'))
            uid = str(uid, 'utf-8')
        except:
            return {'message': 'faild'}

        try:
            user = User.objects.get(wk=uid)
        except:
            return {'message': 'faild'}

        if set_type > 3:
            return {'message': 'faild'}

        if set_type == 1:
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
