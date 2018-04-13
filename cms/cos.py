import time
import logging
import hmac
import hashlib
import requests
import urllib
from urllib.parse import quote
from requests.auth import AuthBase
from requests import Request, Session

def format_region(region):
    """格式化地域"""
    if not region:
        print ("region is required not empty!")
    if region.find('cos.') != -1:
        return region  # 传入cos.ap-beijing-1这样显示加上cos.的region
    if region == 'cn-north' or region == 'cn-south' or region == 'cn-east' or region == 'cn-south-2' or region == 'cn-southwest' or region == 'sg':
        return region  # 老域名不能加cos.
    #  支持v4域名映射到v5
    if region == 'cossh':
        return 'cos.ap-shanghai'
    if region == 'cosgz':
        return 'cos.ap-guangzhou'
    if region == 'cosbj':
        return 'cos.ap-beijing'
    if region == 'costj':
        return 'cos.ap-beijing-1'
    if region == 'coscd':
        return 'cos.ap-chengdu'
    if region == 'cossgp':
        return 'cos.ap-singapore'
    if region == 'coshk':
        return 'cos.ap-hongkong'
    if region == 'cosca':
        return 'cos.na-toronto'
    if region == 'cosger':
        return 'cos.eu-frankfurt'

    return 'cos.' + region  # 新域名加上cos.


def format_bucket(bucket, appid):
    """兼容新老bucket长短命名,appid为空默认为长命名,appid不为空则认为是短命名"""
    if not isinstance(bucket, str):
        print ("bucket is not str")
    # appid为空直接返回bucket
    if not appid:
        return bucket
    # appid不为空,检查是否以-appid结尾
    if bucket.endswith("-"+appid):
        return bucket
    return bucket + "-" + appid


def format_path(path):
    """检查path是否合法,格式化path"""
    if not isinstance(path, str):
        print ("your Key is not str")
    if path == "":
        print ("Key can't be empty string")
    if path[0] == '/':
        path = path[1:]
    # 提前对path进行encode
    path = quote(path, '/-_.~')
    return path

def to_unicode(s):
    # if isinstance(s, unicode):
    #     return s
    # else:
    return s


def get_md5(data):
    m2 = hashlib.md5(data)
    MD5 = base64.standard_b64encode(m2.digest())
    return MD5


maplist = {
            'ContentLength': 'Content-Length',
            'ContentMD5': 'Content-MD5',
            'ContentType': 'Content-Type',
            'CacheControl': 'Cache-Control',
            'ContentDisposition': 'Content-Disposition',
            'ContentEncoding': 'Content-Encoding',
            'ContentLanguage': 'Content-Language',
            'Expires': 'Expires',
            'ResponseContentType': 'response-content-type',
            'ResponseContentLanguage': 'response-content-language',
            'ResponseExpires': 'response-expires',
            'ResponseCacheControl': 'response-cache-control',
            'ResponseContentDisposition': 'response-content-disposition',
            'ResponseContentEncoding': 'response-content-encoding',
            'Metadata': 'Metadata',
            'ACL': 'x-cos-acl',
            'GrantFullControl': 'x-cos-grant-full-control',
            'GrantWrite': 'x-cos-grant-write',
            'GrantRead': 'x-cos-grant-read',
            'StorageClass': 'x-cos-storage-class',
            'Range': 'Range',
            'IfMatch': 'If-Match',
            'IfNoneMatch': 'If-None-Match',
            'IfModifiedSince': 'If-Modified-Since',
            'IfUnmodifiedSince': 'If-Unmodified-Since',
            'CopySourceIfMatch': 'x-cos-copy-source-If-Match',
            'CopySourceIfNoneMatch': 'x-cos-copy-source-If-None-Match',
            'CopySourceIfModifiedSince': 'x-cos-copy-source-If-Modified-Since',
            'CopySourceIfUnmodifiedSince': 'x-cos-copy-source-If-Unmodified-Since',
            'VersionId': 'versionId',
            'ServerSideEncryption': 'x-cos-server-side-encryption',
            'SSECustomerAlgorithm': 'x-cos-server-side-encryption-customer-algorithm',
            'SSECustomerKey': 'x-cos-server-side-encryption-customer-key',
            'SSECustomerKeyMD5': 'x-cos-server-side-encryption-customer-key-MD5',
            'SSEKMSKeyId': 'x-cos-server-side-encryption-cos-kms-key-id'
           }


def mapped(headers):
    """S3到COS参数的一个映射"""
    _headers = dict()
    for i in headers.keys():
        if i in maplist:
            _headers[maplist[i]] = headers[i]
        else:
            raise CosClientError('No Parameter Named '+i+' Please Check It')
    return _headers


def filter_headers(data):
    """只设置host content-type 还有x开头的头部.

    :param data(dict): 所有的头部信息.
    :return(dict): 计算进签名的头部.
    """
    headers = {}
    for i in data.keys():
        if i == 'Content-Type' or i == 'Host' or i[0] == 'x' or i[0] == 'X':
            headers[i] = data[i]
    return headers


def to_string(data):
    """转换unicode为string.

    :param data(unicode|string): 待转换的unicode|string.
    :return(string): 转换后的string.
    """
    # if isinstance(data, unicode):
    #     return data.encode('utf8')
    return data.encode('utf-8')


class CosS3Auth(AuthBase):

    def __init__(self, secret_id, secret_key, key='', params={}, expire=600):
        self._secret_id = to_string(secret_id)
        self._secret_key = to_string(secret_key)
        self._expire = expire
        self._params = params
        if key:
            if key[0] == '/':
                self._path = key
            else:
                self._path = '/' + key
        else:
            self._path = '/'

    def __call__(self, r):
        path = self._path
        uri_params = self._params
        headers = filter_headers(r.headers)
        # reserved keywords in headers urlencode are -_.~, notice that / should be encoded and space should not be encoded to plus sign(+)
        headers = dict([(k.lower(), quote(v, '-_.~')) for k, v in headers.items()])  # headers中的key转换为小写，value进行encode
        keys = lambda x_y: "%s=%s" % (x_y[0], x_y[1])
        format_str = "{method}\n{host}\n{params}\n{headers}\n".format(
            method=r.method.lower(),
            host=path,
            params=urllib.parse.urlencode(sorted(uri_params.items())),
            headers='&'.join(map(keys, sorted(headers.items())))
        )

        start_sign_time = int(time.time())
        sign_time = "{bg_time};{ed_time}".format(bg_time=start_sign_time-60, ed_time=start_sign_time+self._expire)
        sha1 = hashlib.sha1()
        sha1.update(str(format_str).encode('utf-8'))

        str_to_sign = "sha1\n{time}\n{sha1}\n".format(time=sign_time, sha1=sha1.hexdigest())
        sign_key = hmac.new(str(self._secret_key).encode('utf-8'), str(sign_time).encode('utf-8'), hashlib.sha1).hexdigest()
        sign = hmac.new(sign_key.encode('utf-8'), str_to_sign.encode('utf-8'),hashlib.sha1).hexdigest()

        sign_tpl = "q-sign-algorithm=sha1&q-ak={ak}&q-sign-time={sign_time}&q-key-time={key_time}&q-header-list={headers}&q-url-param-list={params}&q-signature={sign}"

        r.headers['Authorization'] = sign_tpl.format(
            ak=self._secret_id.decode('utf-8'),
            sign_time=sign_time,
            key_time=sign_time,
            params=';'.join(sorted(map(lambda k: k.lower(), uri_params.keys()))),
            headers=';'.join(sorted(headers.keys())),
            sign=sign
        )
        return r


class CosConfig(object):
    """config类，保存用户相关信息"""
    def __init__(self, Appid=None, Region=None, Secret_id=None, Secret_key=None, Token=None, Scheme=None, Timeout=None, Access_id=None, Access_key=None):
        """初始化，保存用户的信息

        :param Appid(string): 用户APPID.
        :param Region(string): 地域信息.
        :param Secret_id(string): 秘钥SecretId.
        :param Secret_key(string): 秘钥SecretKey.
        :param Token(string): 临时秘钥使用的token.
        :param Schema(string): http/https
        :param Timeout(int): http超时时间.
        :param Access_id(string): 秘钥AccessId(兼容).
        :param Access_key(string): 秘钥AccessKey(兼容).
        """
        self._appid = Appid
        self._region = format_region(Region)
        self._token = Token
        self._timeout = Timeout

        if Scheme is None:
            Scheme = 'http'
        if(Scheme != 'http' and Scheme != 'https'):
            print ('Scheme can be only set to http/https')
        self._scheme = Scheme

        # 兼容(SecretId,SecretKey)以及(AccessId,AccessKey)
        if(Secret_id and Secret_key):
            self._secret_id = Secret_id
            self._secret_key = Secret_key
        elif(Access_id and Access_key):
            self._secret_id = Access_id
            self._secret_key = Access_key
        else:
            print ('SecretId and SecretKey is Required!')

    def uri(self, bucket, path=None, scheme=None, region=None):
        """拼接url

        :param bucket(string): 存储桶名称.
        :param path(string): 请求COS的路径.
        :return(string): 请求COS的URL地址.
        """
        bucket = format_bucket(bucket, self._appid)
        if scheme is None:
            scheme = self._scheme
        if region is None:
            region = self._region
        if path is not None:
            if path == "":
                print ("Key can't be empty string")
            if path[0] == '/':
                path = path[1:]
            url = u"{scheme}://{bucket}.{region}.myqcloud.com/{path}".format(
                scheme=scheme,
                bucket=to_unicode(bucket),
                region=region,
                path=to_unicode(path)
            )
        else:
            url = u"{scheme}://{bucket}.{region}.myqcloud.com/".format(
                scheme=self._scheme,
                bucket=to_unicode(bucket),
                region=self._region
            )
        return url


class CosS3Client(object):
    """cos客户端类，封装相应请求"""
    def __init__(self, conf, retry=1, session=None):
        """初始化client对象

        :param conf(CosConfig): 用户的配置.
        :param retry(int): 失败重试的次数.
        :param session(object): http session.
        """
        self._conf = conf
        self._retry = retry  # 重试的次数，分片上传时可适当增大
        if session is None:
            self._session = requests.session()
        else:
            self._session = session

    def get_auth(self, Method, Bucket, Key='', Expired=300, Headers={}, Params={}):
        """获取签名

        :param Method(string): http method,如'PUT','GET'.
        :param Bucket(string): 存储桶名称.
        :param Key(string): 请求COS的路径.
        :param Expired(int): 签名有效时间,单位为s.
        :param headers(dict): 签名中的http headers.
        :param params(dict): 签名中的http params.
        :return (string): 计算出的V5签名.

        .. code-block:: python

            config = CosConfig(Region=region, Secret_id=secret_id, Secret_key=secret_key, Token=token)  # 获取配置对象
            client = CosS3Client(config)
            # 获取上传请求的签名
            auth_string = client.get_auth(
                    Method='PUT'
                    Bucket='bucket',
                    Key='test.txt',
                    Expired=600,
                    Headers={'header1': 'value1'},
                    Params={'param1': 'value1'}
                )
            print auth_string
        """
        url = self._conf.uri(bucket=Bucket, path=quote(Key, '/-_.~'))
        r = Request(Method, url, headers=Headers, params=Params)
        auth = CosS3Auth(self._conf._secret_id, self._conf._secret_key, Key, Params, Expired)
        return auth(r).headers['Authorization']
    
    def send_request(self, method, url, timeout=30, **kwargs):
        """封装request库发起http请求"""
        if self._conf._timeout is not None:  # 用户自定义超时时间
            timeout = self._conf._timeout
        if self._conf._token is not None:
            kwargs['headers']['x-cos-security-token'] = self._conf._token
        kwargs['headers']['User-Agent'] = 'cos-python-sdk-v5.1.4.0'
        try:
            for j in range(self._retry):
                if method == 'POST':
                    res = self._session.post(url, timeout=timeout, **kwargs)
                elif method == 'GET':
                    res = self._session.get(url, timeout=timeout, **kwargs)
                elif method == 'PUT':
                    res = self._session.put(url, timeout=timeout, **kwargs)
                elif method == 'DELETE':
                    res = self._session.delete(url, timeout=timeout, **kwargs)
                elif method == 'HEAD':
                    res = self._session.head(url, timeout=timeout, **kwargs)
                if res.status_code < 400:  # 2xx和3xx都认为是成功的
                    return res
        except Exception as e:  # 捕获requests抛出的如timeout等客户端错误,转化为客户端错误
            print (str(e))

        if res.status_code >= 400:  # 所有的4XX,5XX都认为是COSServiceError
            if method == 'HEAD' and res.status_code == 404:   # Head 需要处理
                info = dict()
                info['code'] = 'NoSuchResource'
                info['message'] = 'The Resource You Head Not Exist'
                info['resource'] = url
                info['requestid'] = res.headers['x-cos-request-id']
                info['traceid'] = res.headers['x-cos-trace-id']
                print (method, info, res.status_code)
            else:
                msg = res.text
                if msg == '':  # 服务器没有返回Error Body时 给出头部的信息
                    msg = res.headers
                print (method, msg, res.status_code)

        return None

    def put_object(self, Bucket, Body, Key, EnableMD5=False, **kwargs):
        """单文件上传接口，适用于小文件，最大不得超过5GB

        :param Bucket(string): 存储桶名称.
        :param Body(file|string): 上传的文件内容，类型为文件流或字节流.
        :param Key(string): COS路径.
        :param EnableMD5(bool): 是否需要SDK计算Content-MD5，打开此开关会增加上传耗时.
        :kwargs(dict): 设置上传的headers.
        :return(dict): 上传成功返回的结果，包含ETag等信息.

        .. code-block:: python

            config = CosConfig(Region=region, Secret_id=secret_id, Secret_key=secret_key, Token=token)  # 获取配置对象
            client = CosS3Client(config)
            # 上传本地文件到cos
            with open('test.txt', 'rb') as fp:
                response = client.put_object(
                    Bucket='bucket',
                    Body=fp,
                    Key='test.txt'
                )
                print response['ETag']
        """
        headers = mapped(kwargs)
        if 'Metadata' in headers.keys():
            for i in headers['Metadata'].keys():
                headers[i] = headers['Metadata'][i]
            headers.pop('Metadata')

        url = self._conf.uri(bucket=Bucket, path=quote(Key, '/-_.~'))  # 提前对key做encode
        print("put object, url=:{url} ,headers=:{headers}".format(
            url=url,
            headers=headers))
        # Body = deal_with_empty_file_stream(Body)
        # if EnableMD5:
        #     md5_str = get_content_md5(Body)
        #     if md5_str:
        #         headers['Content-MD5'] = md5_str
        rt = self.send_request(
            method='PUT',
            url=url,
            auth=CosS3Auth(self._conf._secret_id, self._conf._secret_key, Key),
            data=Body,
            headers=headers)
        print (rt)
        response = rt.headers
        return response


def get_auth(Method, keys, params,headers=None):
    conf = CosConfig(Appid='1252731440',Region='ap-beijing',Secret_id='AKIDNnhTFsGxOebmyMLw7yDIvvrhMFB1K9A8', Secret_key='gHjNyW2Uq0yW0MbfCvlendNw1wlNvOjh')

    auth = CosS3Client(conf=conf)
    auth_string = auth.get_auth(
            Method='POST',
            Bucket='test-12345-1252731440',
            Key=keys,
            Expired=600
    )
    return auth_string

# conf = CosConfig(Region='ap-beijing',Secret_id='AKIDNnhTFsGxOebmyMLw7yDIvvrhMFB1K9A8', Secret_key='gHjNyW2Uq0yW0MbfCvlendNw1wlNvOjh')

# auth = CosS3Client(conf=conf)

# with open('tests.py', 'rb') as fp:
#     response = auth.put_object(
#         Bucket='test-12345-1252731440',
#         Body=fp,
#         Key='tests.py',
#         StorageClass='STANDARD',
#         CacheControl='no-cache',
#         ContentDisposition='download.txt'
#     )
#     print (response['ETag'])