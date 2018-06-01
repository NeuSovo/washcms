import time
import json
import hashlib
import logging
from cms.models import *
from cms.tools import *
from django.http import JsonResponse
from datetime import datetime, timedelta
from cms.apps import APIServerErrorCode as ASEC
from cms.apps import RedisExpireTime as ret

app = logging.getLogger('app.custom')
request_backup = logging.getLogger('app.backup')


def parse_info(data):
    """
    parser_info:
    param must be a dict
    parse dict data to json,and return HttpResponse
    """
    return JsonResponse(data)


def usercheck(user_type=-1):
    def wrapper(func):
        def inner_wrapper(*args, **kwargs):
            result = {}
            request = args[0]

            action = request.GET.get('action', None) or kwargs.get(
                'action', None) or 'None'

            try:
                body = json.loads(request.body)
                wckey = body['base_req']['wckey']
            except:
                result['code'] = ASEC.ERROR_PARAME
                result['message'] = ASEC.getMessage(ASEC.ERROR_PARAME)
                response = parse_info(result)
                response.status_code = 400

                return response

            if redis_session.exists(wckey):
                wk = redis_session.get(wckey).decode('utf-8')
            else:
                result['code'] = ASEC.SESSION_NOT_WORK
                result['message'] = ASEC.getMessage(ASEC.SESSION_NOT_WORK)
                return parse_info(result)            

            user = User.objects.get(wk=str(wk))

            body.pop('base_req')
            request_backup.info("[{action}][{user}][{body}]".format(
                                action=request.path,
                                user=str(user),body=body))

            if user_type == -1 or user.user_type <= user_type:
                return func(*args, **kwargs, user=user, body=body)
            else:
                return parse_info({'message': 'user_type failed'})

        return inner_wrapper

    return wrapper


class WechatSdk(object):

    """
    WechatSdk
    Based on Wechat user code
    """
    openid = ''
    wxsskey = ''

    def __init__(self, code):
        super(WechatSdk, self).__init__()
        self.code = code

    def check(self):
        res = get_openid(self.code)
        if res:
            self.openid = res['openid']
            self.wxsskey = res['session_key']
            return True
        else:
            return False

    def save_user(self):
        have_user = User.objects.filter(wk=self.openid)
        if have_user.exists():
            # 已注册过
            return self.flush_session()

        sess = gen_hash()
        redis_session.set(sess,self.openid,ex=ret.redis_session)
        user = User(wk=self.openid)
        user.save()
        # 自动为用户生成Profile
        # Profile(wk=user).save()

        # 注册成功，分配cookie
        return {'sess': sess,
                'code': ASEC.REG_SUCCESS,
                'message': ASEC.getMessage(ASEC.REG_SUCCESS)}

    def flush_session(self):
        sess = gen_hash()
        redis_session.set(sess,self.openid,ex=ret.redis_session)
        # 刷新Cookie成功
        return {'sess': sess,
                'code': ASEC.FLUSH_SESSION_SUCCESS,
                'message': ASEC.getMessage(ASEC.FLUSH_SESSION_SUCCESS)}


class LoginManager(object):
    TOKEN = 'eq021n!3'

    def __init__(self, user):
        super(LoginManager, self).__init__()
        self.user = user

    def __str__(self):
        return self.user

    def check(self, sign, checktime):
        if time.time() - int(checktime) > 5:
            return False

        check_str = en_md5(str(self.TOKEN) + str(checktime))

        if settings.DEBUG:
            return True
        else:
            return check_str == sign

    def reply(self):
        user = self.user
        user.last_login = datetime.now()
        user_info = UserManager.get_user_info(user)

        if not settings.DEBUG:
            user_info['qrcode'] = 'https://wash.wakefulness.cn/tools/qrcode/' + \
                                  user_info['qrcode']
        user.save()

        return {'code': ASEC.LOGIN_SUCCESS,
                'user_type': user.user_type,
                'info': user_info,
                'message': ASEC.getMessage(ASEC.LOGIN_SUCCESS)}


class UserManager(object):

    @staticmethod
    def get_user(wckey=None):
        """
        :param wckey:
        :return: user
        """
        if None:
            return None

        user_key = Session.objects.get(session_data=wckey)
        user = User.objects.get(wk=user_key.session_key)

        return user

    @staticmethod
    def get_user_info(user):
        """
        :param user:
        :return: name,avatar_links
                and base64(user.wk)
        """
        name = user.nick_name
        avatar_links = user.avatar_links

        return {'name': name,
                'avatar_links': avatar_links,
                'user_type': user.user_type,
                'qrcode': en_base64(user.wk)}

    @staticmethod
    def get_user_store(user):
        """
        User_type must be 3
        :param user:
        :return: Customer User store id
        """
        return CustomerProfile.objects.get(wk=user)

    @staticmethod
    def get_user_area(user):
        """
        User_type must be 2
        :param user:
        :return: Courier User Area id
        """
        return PeisongProfile.objects.get(wk=user)

    @staticmethod
    def set_user_profile(user, profile):
        """
        :param user:
        :param profile:
        :return:
        """
        user.nick_name = profile.get('name','nick_name')
        user.avatar_links = profile.get('url','https://pic3.zhimg.com/aadd7b895_s.jpg')
        user.save()

        return user

    @staticmethod
    def set_user_store_profile(user, profile):
        """
        only user type is 3
        """
        store = UserManager.get_user_store(user).store

        store.store_addr = profile['addr']
        store.store_phone = int(profile['phone'])
        store.store_name = profile['name']
        store.save()

        return store

    @staticmethod
    def get_user_store_profile(user):
        """
        only user type is 3
        """
        profile = {}
        store = UserManager.get_user_store(user).store

        profile['addr'] = store.store_addr
        profile['phone'] = store.store_phone
        profile['name'] = store.store_name

        return profile

    @staticmethod
    def set_user_peisong_profile(user, profile):
        try:
            phone = int(profile['phone'])
        except Exception as e:
            app.info(str(e))
            return

        peisong = PeisongProfile.objects.get(wk=user)
        peisong.name = profile['name']
        peisong.phone = phone
        peisong.save()

        return peisong

    @staticmethod
    def get_user_peisong_profile(user):
        peisong = PeisongProfile.objects.get(wk=user)
        return {'area_id': peisong.area.id,
                'area_name': peisong.area.area_name,
                'name': peisong.name,
                'phone': peisong.phone}

    @staticmethod
    def set_user_type(user, set_type, area=None):
        """
        set_type = 0,1,2PeisongProfile
        """
        if set_type == 2:
            PeisongProfile(wk=user, area=area).save()

        if set_type == 4:
            if user.user_type == 2:
                to_delete = PeisongProfile.objects.get(wk=user)
                for i in PickOrder.objects.filter(pick_user=PeisongProfile.objects.get(wk=user)):
                    PickOrderDetail.objects.filter(
                        order_id=i.order_id).delete()
                    i.delete()
                to_delete.delete()

            for i in redis_session.keys():
                if redis_session.get(i).decode('utf-8') == user.wk:
                    redis_session.delete(i)
        user.user_type = set_type
        user.save()
        return user
