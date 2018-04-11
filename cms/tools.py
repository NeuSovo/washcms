import os
import redis
import base64
import qrcode
import requests
from hashlib import sha256, md5
from django.conf import settings
from django.utils.six import BytesIO

APPID = 'wx5c7d55175f3872b7'
SECRET = '6050b3ca9c9b3823768ae1867ef9036e'
redis_report = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)

def gen_hash():
    """
    gen_hash as session data.
    The repetition should be a very small probability event,
    and from a statistical point of view, the probability is zero.
    Return a string of length 64.
    """
    return sha256(os.urandom(24)).hexdigest()


def gen_qrcode(data):
    img = qrcode.make(data)

    buf = BytesIO()
    img.save(buf)
    image_stream = buf.getvalue()

    return image_stream


def get_openid(code):
    params = {
        'appid': APPID,
        'secret': SECRET,
        'js_code': code,
        'grant_type': 'authorization_code'
    }

    try:
        data = requests.get(
            'https://api.weixin.qq.com/sns/jscode2session', params=params)
    except Exception as e:
        return False

    info = data.json()

    if 'openid' not in info:
        if settings.DEBUG:
            info = {
                'openid': code,
                'session_key': 'SESSIONKEY',
            }
        else:
            return False

    return info


def en_md5(enstr):
    enstr = str(enstr)
    enstr = enstr.encode('utf-8')
    m = md5()
    m.update(enstr)

    return m.hexdigest()


def en_base64(txt):
    tmp = base64.b64encode(str(txt).encode('utf-8'))
    return str(tmp, 'utf-8')


def de_base64(txt):
    uid = base64.b64decode(txt.encode('utf-8'))
    uid = str(uid, 'utf-8')

    return uid