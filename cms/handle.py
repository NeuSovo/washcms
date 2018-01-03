# -*- coding: utf-8 -*-
import os
import time
import logging
import requests
from hashlib import sha256, md5

from django.conf import settings
from datetime import datetime, timedelta

from .models import *
from .apps import APIServerErrorCode as ASEC
app = logging.getLogger('app.custom')


class WechatSdk(object):
    __Appid = 'wx5c7d55175f3872b7'
    __SECRET = '18e18b264801eb53c9fe7634504f2f15'
    """
    WechatSdk
        nothing
    """

    def __init__(self, code):
        super(WechatSdk, self).__init__()
        self.code = code

    def gen_hash(self):
        return (sha256(os.urandom(24)).hexdigest())

    def get_openid(self):
        s = requests.Session()
        params = {
            'appid': self.__Appid,
            'secret': self.__SECRET,
            'js_code': self.code,
            'grant_type': 'authorization_code'
        }

        if settings.DEBUG:
            info = {
                'openid': self.code,
                'session_key': 'SESSIONKEY',
            }
        else:
            try:
                data = s.get(
                    'https://api.weixin.qq.com/sns/jscode2session', params=params)
            except Exception as e:
                app.error(str(e) + '\tcode:' + str(self.code))
                return False
                
            info = data.json()

        if 'openid' not in info:
            app.info('parameter \'{}\' error'.format(self.code))
            return False
        else:
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
        Profile(wk=user).save()

        # 注册成功，分配cookie
        return {'sess': sess,
                'code': ASEC.REG_SUCCESS,
                'message': ASEC.getMessage(ASEC.REG_SUCCESS)}

    def flush_session(self):
        this_user = Session.objects.get(session_key=self.openid)
        sess = self.gen_hash()

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

    def get_info(self, user):
        name = user.profile.name
        return {'name': name}

    # def get_type(self, user):
    #     user_type = 3
    #     if user.is_admin:
    #         user_type = 0
    #     if user.is_courier:
    #         user_type = 1
    #     if user.is_customer:
    #         user_type = 2

    #     return user_type

    def reply(self):
        try:
            user_key = Session.objects.get(session_data=self.wckey)
        except Exception as e:
            app.error(str(e) + 'wckey:{}'.format(self.wckey))
            return {'code': ASEC.SESSION_NOT_WORK,
                    'message': ASEC.getMessage(ASEC.SESSION_NOT_WORK)}

        if user_key.expire_date < datetime.now():
            return {'code': ASEC.SESSION_EXPIRED,
                    'message': ASEC.getMessage(ASEC.SESSION_EXPIRED)}

        user = User.objects.get(wk=user_key.session_key)

        user_info = self.get_info(user)

        return {'code': ASEC.LOGIN_SUCCESS,
                'type': user.user_type,
                'info': user_info,
                'message': ASEC.getMessage(ASEC.LOGIN_SUCCESS)}
