import hashlib
import random
import os
import threading
import blist
import bencode
import zope.interface
import heapq
import socket
import struct
import blist
import operator

try:
    # python2.7 and python3k
    from weakref import WeakSet
except ImportError:
    # run: pip install weakrefset
    # http://pypi.python.org/pypi/weakrefset
    from weakrefset import WeakSet

str_to_int = lambda s: reduce(lambda a, b: ord(b) + (a << 8), s, 0)
def int_to_str(i):
    buf = b''
    while i > 0:
        buf += chr(i % 256)
        i >>= 8
    return b''.join(reversed(buf))


class IDHTObserver(zope.interface.Interface):
    def notify(message_type, message):
        """
        """


class HashingTokenManager(object):
    def __init__(self, token_len=2, random_data=None, digest_algo=hashlib.sha256):
        if random_data is None:
           random_data = os.urandom(128)
        self._token_len = token_len
        self._random_data = random_data
        self._digest_algo = digest_algo

    def acquire(self, compactible):
        return hashlib.sha256(self._random_data + (compactible.compact()) + \
                self._random_data).digest()[0:self._token_len]

    def check(self, compactible, token):
        return token == self.acquire(compactible)


class PeerList(object):
    MAX_AGE = 900 # in seconds

    def __init__(self):
        self.peers = dict()

    def add_peer(self, endpoint):
        self.peers[endpoint] = time.time()

    def cleanup(self):
        for peer, last_bumped in list(self.peers.items()):
            if last_bumped + self.MAX_AGE > time.time():
                del self.peers[peer]

    def __len__(self):
        return len(self.peers)


class AnnounceList(object):
    class Handle(object): pass

    def __init__(self):
        self._items = dict()

    def add(self, info_hash, port):
        key = self.Handle()
        self._items[key] = (info_hash, port)
        return key

    def remove(self, key):
        del self._items[key]

    def __iter__(self):
        return iter(list(self._items.iteritems()))


class Tracker(object):
    def __init__(self):
        self.peer_lists = dict()

    def add_peer(self, infohash, endpoint):
        if infohash not in self.peer_lists:
            self.peer_lists[infohash] = PeerList()
        self.peer_lists[infohash].add_peer(endpoint)

    def cleanup(self):
        for info_hash, peer_list in list(self.peer_lists.items()):
            peer_list.cleanup()
            if 0 == len(peer_list):
                del self.peer_lists[info_hash]


class DHTNodeID(object):
    def __init__(self, node_id):
        if isinstance(node_id, str):
            node_id = int(DHTNodeID.from_bytea(node_id))
        elif isinstance(node_id, DHTNodeID):
            node_id = node_id.node_id
        if node_id is None:
            node_id = 0
        self._id = node_id

    @classmethod
    def from_bytea(self, bytea):
        assert 20 == len(bytea), "must be length 20 (160 bits)"
        return DHTNodeID(str_to_int(bytea))

    @property
    def node_id(self):
        return self._id

    def distance(self, other):
        return type(self)(self.node_id ^ other.node_id)

    def __int__(self):
        return int(self._id)

    def __cmp__(self, other):
        return cmp(self._id, other._id)

    def __str__(self):
        return "%040x" % self._id

    def __repr__(self):
        return "<DHTNodeID %s>" % str(self)

    def to_bin(self):
        return str(self).decode('hex')


class UDPEndpoint(object):
    def __init__(self, ip, port):
        self._ip = ip
        self._port = port

    def compact(self):
        return socket.inet_aton(self._ip) + struct.pack("!H", self._port)

    @classmethod
    def from_compact(cls, compact_str):
        ip = socket.inet_ntoa(compact_str[0:4])
        port, = struct.unpack("!H", compact_str[4:6])
        return UDPEndpoint(ip, port)

    @classmethod
    def decompact(cls, str_):
        return map(cls.from_compact, (str_[i:i+6] for i in range(0, len(str_), 6)))

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port


class DHTNode(object):
    def __init__(self, node_id, ip, port):
        self._id = DHTNodeID(node_id)
        self._ip = ip
        self._port = port

    def __int__(self):
        return int(self._id)

    def compact(self):
        return socket.inet_aton(self._ip) + struct.pack("!H", self._port)

    @classmethod
    def from_endpoint(cls, endpoint, node_id):
        return cls(DHTNodeID(node_id), endpoint.ip, endpoint.port)

    @classmethod
    def from_compact(cls, compact_str):
        ip = socket.inet_ntoa(compact_str[0:4])
        port, = struct.unpack("!H", compact_str[4:6])
        return (ip, port)

    @classmethod
    def decompact(cls, str_):
        return map(cls.from_compact, (str_[i:i+6] for i in range(0, len(str_), 6)))

    @property
    def node_id(self):
        return self._id

    @property
    def address(self):
        return (self._ip, self._port)

    def __repr__(self):
        return "<DHTNode %s %s:%d>" % (str(self._id), self._ip, self._port)


class DHTBucketNodeRecord(object):
    MAX_GOOD_AGE = 15*60 # max age before the node stops bein `good' 
    BADNESS_THRESHOLD = 4

    def __init__(self, dht_node, last_seen):
        self._badness = 0
        self._node = dht_node
        if last_seen is None:
            last_seen = time.time()
        self._last_seen = last_seen

    def is_good(self):
        return self.age + self.MAX_GOOD_AGE <= time.time()

    def is_bad(self):
        return not self.is_good() and \
                self._badness >= self.BADNESS_THRESHOLD

    def is_questionable(self):
        return time.time() < self.age + self.MAX_GOOD_AGE and \
                self._badness < self.BADNESS_THRESHOLD

    def __state_str(self):
        if self.is_good(): return "good"
        if self.is_questionable(): return "questionable"
        if self.is_bad(): return "bad"

    @property
    def node(self):
        return self._node

    @property
    def age(self):
        return time.time() - self._last_seen

    def bump(self):
        self._last_seen = time.time()
        self._badness = 0

    def unbump(self): # XXX
        self._badness += 1

    def __repr__(self):
        return "<DHTBucketNodeRecord %s age=%.1fs dht_node=%s>" % (
                self.__state_str(), self.age, repr(self._node))


class DHTBucketNode(object):
    """
    Can contain items who have IDs in min <= item_id < max

    This class should be Thread-safe
    """
    # TODO: fix datastructure, this tree is degenerate
    # Within this class, an `item' is a DHTNode and a `node' is part of the tree
    MAX_ITEMS = 8

    def __init__(self, our_id, minimum_id=None, maximum_id=None):
        assert our_id is not None
        self._mut_lock = threading.Lock()
        self._our_id = our_id
        self._min = minimum_id is not None and minimum_id or 0
        self._max = maximum_id is not None and maximum_id or 2**160
        self._children = None
        self._items = blist.sortedlist(key=lambda item: item.node.node_id)

    def is_interior_node(self):
        assert (self._items is not None) ^ (self._children is not None)
        return self._items is None and self._children is not None

    def is_leaf_node(self):
        assert (self._items is not None) ^ (self._children is not None)
        return self._children is None and self._items is not None

    def is_full(self):
        return len(self._items) >= self.MAX_ITEMS

    def accepts_id(self, id):
        return self._min <= id < self._max

    def accepts_item(self, item):
        return self._min <= item.node.node_id < self._max

    def __split(self):
        left = type(self)(self._our_id, self._min, (self._min + self._max)/2)
        right = type(self)(self._our_id, (self._min + self._max)/2, self._min)
        for item in filter(left.accepts_item, self._items):
            left.add_item(item)
        for item in filter(right.accepts_item, self._items):
            right.add_item(item)
        self._items = None
        self._children = (left, right)

    def __add_item(self, item):
        if self.is_interior_node():
            for ch in self._children:
                if ch.accepts_item(item):
                    return ch.add_item(item)
            raise Exception("Malrouted Node")
        elif self.is_leaf_node():
            if self.is_full():
                # bucket is splittable of bucket contains our ID
                if self.accepts_id(self._our_id):
                    self.__split()
                    return self.__add_item(item)
                return False
            self._items.add(item)
        else:
            raise Exception("Programmer Error")

    def add_item(self, item):
        """
        Lock-protected add item
        """
        if not self.accepts_item(item):
            raise Exception("Unacceptable item")
        with self._mut_lock:
            return self.__add_item(item)

    def __find_item(self, item_id):
        if self.is_interior_node():
            item = False
            for ch in self._children:
                item = item or ch.find_item(item_id)
            return item
        elif self.is_leaf_node(self):
            matching_items = filter(lambda i: i.node.node_id == item_id, self._items)
            if matching_items:
                return matching_items[0]
            return False
        else:
            raise Exception("Programmer Error")

    def find_item(self, item_id):
        """
        Lock-protected find item
        """
        if not self.accepts_id(item_id):
            return False
        with self._mut_lock:
            return self.__find_item(item_id)

    def all_items(self):
        """
        In-order iterable of all items in the tree
        """
        if self.is_interior_node():
            for ch in self._children:
                for i in ch.all_items():
                    yield i
        elif self.is_leaf_node():
            with self._mut_lock:
                for i in self._items:
                    yield i

    def age(self):
        if self.is_interior_node():
            return min(ch.age for ch in self._children)
        elif self.is_leaf_node():
            with self._mut_lock:
                return min(i.age for i in self._items)

    def oldest_bucket(self):
        if self.is_interior_node():
            return max(self._children, key=lambda ch: ch.age).oldest_bucket()
        elif self.is_leaf_node():
            return self

    def oldest_node(self):
        if self.is_interior_node():
            return self.oldest_bucket().oldest_node()
        elif self.is_leaf_node():
            return max(self._items, key=lambda i: i.age)

    def cleanup(self):
        if self.is_interior_node():
            for ch in self._children:
                ch.cleanup()
        elif self.is_leaf_node():
            for item in self._items:
                if item.is_bad():
                    self._items.remove(item)

    def item_count(self):
        raise NotImplementedError

    def child_item_count(self):
        return len(self._children)

    def __repr__(self):
        if self.is_interior_node():
            return "<DHTBucketNode {0x%x <= id < 0x%x} ours=%s %s>" % (
                    self._min, self._max, self.accepts_id(self._our_id),
                    repr(self._children))
        elif self.is_leaf_node():
            return "<DHTBucketNode {0x%x <= id < 0x%x} ours=%s %s>" % (
                    self._min, self._max, self.accepts_id(self._our_id),
                    repr(self._items))
        else:
            raise Exception("Programmer Error")


class DHTRouter(object):
    HANDLERS = list()
    def __init__(self, port):
        self._our_id = DHTNodeID.from_bytea(os.urandom(20))
        self._observers = WeakSet()
        self._buckets = DHTBucketNode(self._our_id)
        self._handlers = list()
        self._token_man = HashingTokenManager()
        self._tracker = Tracker()
        self._announce_list = AnnounceList()

    @property
    def node_id(self):
        return self._our_id

    def add_observer(self, observer_obj):
        if not IDHTObserver.providedBy(observer_obj):
            raise TypeError("add_observer argument must implement interface IDHTObserver")
        self._observers.add(observer_obj)

    def bump_node(self, node):
        node_rec = self._buckets.find_item(int(node))
        if node:
            node_rec.bump()
        else:
            self._token_man.add_node(node)

    @classmethod
    def _cmp_key(cls, requirements, subject):
        for key in requirements.iterkeys():
            if key not in subject:
                return False
        return True

    @classmethod
    def _get_handler(cls, message):
        for key_req, handler_func in cls.HANDLERS:
            if cls._cmp_key(key_req, message):
                return handler_func
        return None

    def process_message(self, src_endpoint, message):
        message_decoded = bencode.bdecode(message)
        handler = self._get_handler(message_decoded)
        if handler is not None:
            response = handler(self, src_endpoint, message_decoded)
            if response is not None:
                self.send_message(src_endpoint, bencode.bencode(response))
        else:
            raise Exception("Unhandled message.: %s" % repr(message_decoded))

    @classmethod
    def add_handler(cls, **key_req):
        def decorator(handler_func):
            cls.HANDLERS.append((key_req, handler_func))
            return handler_func
        return decorator

    def add_announce(self, info_hash, port):
        return self._announce_list.add(info_hash, port)

    def bootstrap_with_endpoint(self, endpoint=None):
        token = self._token_man.acquire(endpoint)
        self.send_message(endpoint, {
                'q': 'ping', 't': token, 'y': 'q', 'a': {
                'id': self.node_id.to_bin()
            } } )

    def continue_bootstrap(self):
        # get_peers on self.node_id
        # get_peers on any underfilled bucket
        pass

    def cleanup(self):
        self._buckets.cleanup()
        oldest_node = self._buckets.oldest_node()
        oldest_node.unbump()
        # send ping to oldest_node



@DHTRouter.add_handler(q='ping', y='q')
def ping_handler_q(router, src_endpoint, ping_message):
    assert 't' in ping_message, "Malformed ping message"
    router.send_message(src_endpoint, {
            't': ping_message['t'],
            'y': 'r',
            'r': {
                'id': router.node_id.to_bin()
            }
        } )


@DHTRouter.add_handler(y='r')
def ping_handler_r(router, src_endpoint, ping_message):
    print repr((router, src_endpoint, ping_message))
    assert 'id' in ping_message['r'], "Malformed ping message"
    if router._token_man.check(src_endpoint, ping_message['t']):
        router.bump_node(DHTNode.from_endpoint(src_endpoint, ping_message['r']['id']))
    # router._token_man.release(ping_message['t'])


@DHTRouter.add_handler(q='find_node', y='q')
def find_node_handler_q(router, src_endpoint, find_node_message):
    assert 'id' in find_node_message['a']
    assert 'target' in find_node_message['a']
    req_node_id = DHTNodeID.from_bytea(find_node_message['a']['id'])

    # We'll just scan the whole list, since it is fairly small.
    good_nodes = itertools.ifilter(DHTBucketNodeRecord.is_good, dht_router.all_items())
    close_nodes = heapq.nsmallest(8, good_nodes,
            lambda item: item.node.node_id.distance(req_node_id))
    if nodes[0].node_id == req_node_id:
        nodes = nodes[0:1] # if we have the node asked for, just return it.
    router.send_message(src_endpoint, {
            't': find_node_message['t'],
            'y': 'r',
            'r': {
                'id': router.node_id.to_bin(),
                'nodes': bencode.bencode(map(DHTNode.compact, nodes))
            }
        } )


@DHTRouter.add_handler(q='find_node', y='r')
def find_node_handler_r(router, src_endpoint, find_node_message):
    assert 'id' in find_node_message['a']
    assert 'nodes' in find_node_message['a']
    # find_node_message.a.id == queried_node_id
    if router._token_man.check(src_endpoint, ping_message['t']):
        router.bump_node(DHTNode.from_endpoint(src_endpoint, ping_message['r']['id']))
    nodes = UDPEndpoint.decompact(find_node_message['a']['nodes'])
    for node in nodes:
        pass
    # do something with nodes.  Add to ping queue?
    pass


@DHTRouter.add_handler(q='get_peers', y='q')
def get_peers_handler_q(router, src_endpoint, get_peers_message):
    assert 'info_hash' in get_peers_message['a']
    assert 'id' in get_peers_message['a']
    pass


@DHTRouter.add_handler(q='get_peers', y='r')
def get_peers_handler_r(router, src_endpoint, get_peers_message):
    if router._token_man.check(src_endpoint, ping_message['t']):
        router.bump_node(DHTNode.from_endpoint(src_endpoint, ping_message['r']['id']))
    peers = UDPEndpoint.decompact(get_peers_message['a']['values'])
    for obs in router._observers:
        obs.notify('get_peers', peers)


@DHTRouter.add_handler(q='announce_peer', y='q')
def announce_peer_handler_q(router, src_endpoint, announce_peer_message):
    assert 'id' in announce_peer_message['a']
    assert 'info_hash' in announce_peer_message['a']
    assert 'port' in announce_peer_message['a']
    assert 'token' in announce_peer_message['a']
    # check if they have our token
    args = announce_peer_message['a']
    if router._token_man.check(src_endpoint, ping_message['t']):
        router.bump_node(DHTNode.from_endpoint(src_endpoint, ping_message['r']['id']))
    if router._token_man.check(args['token'], src_endpoint):
        router._tracker.add_peer((src_endpoint.ip, args['port']), args['info_hash'])
        router.send_message(src_endpoint, {'id': router.node_id.to_bin()})
    else:
        logging.debug("%s sent us a bad token." % repr(src_endpoint))


@DHTRouter.add_handler(q='announce_peer', y='r')
def announce_peer_handler_r(router, src_endpoint, announce_peer_message):
    if router._token_man.check(src_endpoint, ping_message['t']):
        router.bump_node(DHTNode.from_endpoint(src_endpoint, ping_message['r']['id']))
    return
