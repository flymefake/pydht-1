import blist
import bencode
import weakref
import zope.interface

class IDHTObserver(zope.interface.Interface):
    """
    """
    def someevent(foo):
        pass


class DHTNode(object):
    def __init__(self, node_id, ip, port):
        self._id = node_id
        self._ip = ip
        self._port = port

    @property
    def node_id(self):
        return self._id

    def distance(self, other):
        return self._id



class DHTBucket(object)
    MAX_ITEMS = 8
    def __init__(self):
        self._items = blist.sortedlist(key=lambda item: item.node_id)

    def add_node(self, node):
        pass


class DHTBucketTree(object):
    """
    """
    def __init__(self):
        self._min = 0
        self._max = 2**160
        self.children = list()


class DHTRouter(object):
    def __init__(self, port):
        self._observers = weakref.WeakSet()
        self._buckers = DHTBucketTree()

    def add_observer(self, observer_obj):
        if not IDHTObserver.providedBy(observer_obj):
            raise TypeError("add_observer argument must implement interface IDHTObserver")
        self._observers.add(observer_obj)

    def add_handler(self, handler_func):
        pass

