import time
import redis
import base64
import qrcode
import random
import requests
from hashlib import sha256, md5
from django.conf import settings
from django.utils.six import BytesIO

APPID = 'wx5c7d55175f3872b7'
SECRET = '6050b3ca9c9b3823768ae1867ef9036e'
redis_report = redis.StrictRedis(host='127.0.0.1', port=6379, db=0)
redis_session = redis.StrictRedis(host='127.0.0.1', port=6379, db=1)

try:
    random = random.SystemRandom()
    using_sysrandom = True
except NotImplementedError:
    using_sysrandom = False


def gen_hash():
    """
    gen_hash as session data.
    The repetition should be a very small probability event,
    and from a statistical point of view, the probability is zero.
    Return a string of length 64.
    """
    return get_random_string(128)


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

def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-/+'):
    """
    Return a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a 71-bit value. log_2((26+26+10)^12) =~ 71 bits
    """
    if not using_sysrandom:
        # This is ugly, and a hack, but it makes things better than
        # the alternative of predictability. This re-seeds the PRNG
        # using a value that is hard for an attacker to predict, every
        # time a random string is required. This may change the
        # properties of the chosen random sequence slightly, but this
        # is better than absolute predictability.
        random.seed(
            sha256(
                ('%s%s%s' % (random.getstate(), time.time(), settings.SECRET_KEY)).encode()
            ).digest()
        )
    return ''.join(random.choice(allowed_chars) for i in range(length))
