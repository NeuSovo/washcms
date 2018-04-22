import random
from time import time
import requests
import hmac
import hashlib
import binascii
import base64
import urllib

def app_sign(bucket, secret_id, secret_key, cos_path, expired, upload_sign=True):
    appid = '1252731440'
    bucket = bucket
    secret_id = secret_id
    now = int(time())
    rdm = random.randint(0, 999999999)
    cos_path = urllib.parse.quote(cos_path.encode('utf-8'), '~/')
    if upload_sign:
        fileid = '/{}/{}/{}'.format(appid, bucket, cos_path)
    else:
        fileid = cos_path

    if expired != 0 and expired < now:
        expired = now + expired

    # sign_tuple = ()

    plain_text = 'a={}&k={}&e={}&t={}&r={}&f={}&b={}'.format(appid, str(secret_id), expired, now, rdm, fileid, bucket)
    print (plain_text)
    secret_key = secret_key.encode('utf-8')
    sha1_hmac = hmac.new(secret_key, plain_text.encode('utf-8'), hashlib.sha1)
    hmac_digest = sha1_hmac.hexdigest()
    hmac_digest = binascii.unhexlify(hmac_digest)
    sign_hex = hmac_digest + plain_text.encode('utf-8')
    sign_base64 = base64.b64encode(sign_hex)
    return sign_base64,cos_path

def get_auth(key):
    return app_sign(bucket='test-12345-1252731440', secret_id='AKIDNnhTFsGxOebmyMLw7yDIvvrhMFB1K9A8', secret_key='gHjNyW2Uq0yW0MbfCvlendNw1wlNvOjh', cos_path=key, expired=30)


def _sha1_content(content):
    """获取content的sha1

    :param content:
    :return:
    """
    sha1_obj = hashlib.sha1()
    sha1_obj.update(content)
    return sha1_obj.hexdigest()


def upload_single_file(file):
    """ 单文件上传

    :param request:
    :return:
    """
    http_header = dict()
    sign,cos_path = get_auth(file)
    http_header['Authorization'] = sign

    f = open(file, 'rb')
    file_content = f.read()

    http_body = dict()
    http_body['op'] = 'upload'
    http_body['filecontent'] = file_content
    http_body['sha'] = _sha1_content(file_content)
    http_body['biz_attr'] = ''
    http_body['insertOnly'] = 1

    import requests
    info = requests.post('http://test-12345-1252731440.cos.ap-beijing.myqcloud.com/' + cos_path, files=f,data=http_body, headers=http_header)
    return info









