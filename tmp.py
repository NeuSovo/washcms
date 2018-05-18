import redis
# from base64 import standard_b64encode as b64encode
# from datetime import date
# import requests

# parser a quene TVmao
"""
class TvmaoParser(HTMLParser):

    epg_set = None

    divs = 0
    spans = 0

    parse_form = False
    parse_epg = False
    parse_time = False
    parse_program = False

    id = None
    a = None
    q = None

    time = ''
    program = ''

    def __init__(self, epg_set):
        super(TvmaoParser, self).__init__()
        self.epg_set = epg_set

    def handle_starttag(self, tag, attrs):
        if not self.a and not self.q and 'form' == tag:
            self.parse_form = True
        if 'div' == tag:
            self.divs += 1
        if 'span' == tag:
            self.spans += 1

        if not self.parse_epg:
            if attrs:
                if 'class' == attrs[0][0] and 'epg' in attrs[0][1].split():
                    self.divs = 1

                    self.parse_epg = True
                    self.spans = 0

        if self.parse_epg:
            if not self.parse_time:
                if attrs:
                    if 'class' == attrs[0][0] and 'over_hide' in attrs[0][1].split():
                        self.parse_time = True

            if not self.parse_program:
                if attrs:
                    if 'class' == attrs[0][0] and 'p_show' in attrs[0][1].split():
                        self.parse_program = True

        if self.parse_form:
            if 'form' == tag:
                for attr in attrs:
                    if 'a' == attr[0]:
                        self.a = attr[1]
                    if 'q' == attr[0]:
                        self.q = attr[1]

            if 'button' == tag:
                if ('type', 'submit') in attrs:
                    for attr in attrs:
                        if 'id' == attr[0]:
                            self.id = attr[1]

    def handle_endtag(self, tag):
        if 'form' == tag:
            if self.parse_form:
                self.parse_form = False
        if 'div' == tag:
            self.divs -= 1
        if 'span' == tag:
            self.spans -= 1

        if self.parse_epg:
            if not self.divs:
                self.parse_epg = False
                return

            if self.parse_time:
                if 'span' == tag:
                    self.parse_time = False
                return

            if self.parse_program:
                if not self.spans:
                    self.parse_program = False

                    self.epg_set.create(time=self.time, program=self.program)

                    self.time = ''
                    self.program = ''
                return

    def handle_data(self, data):
        if not data.strip():
            return

        if self.parse_epg:
            if self.parse_time:
                self.time = data
            elif self.parse_program:
                self.program += data

    def get_p(self):
        s1 = 'BEJQZkx'[date.today().isoweekday() - 1]
        s2 = b64encode(('%s|%s' % (self.id, self.a)).encode()).decode()
        s3 = b64encode(('|%s' % self.q).encode()).decode()

        return ''.join([s1, s2, s3])
"""

class RedisQueue:
    """docstring for RedisQueue"""

    def __init__(self, name=None, namespace='queue', **redis_kwagrs):
        super(RedisQueue, self).__init__()
        self._key = '%s:%s' % (namespace, name)
        self.__db = redis.Redis(**redis_kwagrs)

    def qsize(self):
        return self.__db.llen(self._key)

    def empty(self):
        return self.qsize() == 0

    def get(self, block=True, timeout=None):
        "if not block, unitl an item is available"
        if block:
            item = self.__db.blpop(self._key, timeout=timeout)
        else:
            item = self.__db.lpop(self._key)
        
        if item:
            item = item[1]

        return item

    def put(self, item):
        return self.__db.rpush(self._key, item)

    def get_nowait(self):
        return self.get(False)

    def __len__(self):
        return self.qsize() 

redis_kwagrs = {
    'host': 'localhost',
    'port': 6379,
    'db': 0
}

# queue = RedisQueue(name='test', **redis_kwagrs)

# print (queue.qsize())