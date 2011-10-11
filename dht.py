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

    def distance(self, other):
        return self._id



class DHTBucket(object)
    MAX_ITEMS = 8
    def __init__(self):
        self._items = blist.sortedlist(key=lambda 

class DHTBucketList(object):
    pass


class DHTRouter(object):
    def __init__(self, port):
        self._observers = weakref.WeakSet()

    def add_observer(self, observer_obj):
        if not IDHTObserver.providedBy(observer_obj):
            raise TypeError("add_observer argument must implement interface IDHTObserver")
        self._observers.add(observer_obj)

    def add_handler(self, handler_func):
        pass

