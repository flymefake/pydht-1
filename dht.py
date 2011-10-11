import threading
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
        return self.node_id ^ other.node_id

    @property
    def address(self):
        return (self._ip, self._port)

    def __repr__(self):
        return "<DHTNode 0x%040x %s:%d>" % (self._id, self._ip, self._port)


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
        self._items = blist.sortedlist(key=lambda item: item.node_id)

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
        return self._min <= item.node_id < self._max

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
            matching_items = filter(lambda i: i.node_id == item_id, self._items)
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
    def __init__(self, port):
        self._observers = weakref.WeakSet()
        self._buckets = DHTBucketTree()

    def add_observer(self, observer_obj):
        if not IDHTObserver.providedBy(observer_obj):
            raise TypeError("add_observer argument must implement interface IDHTObserver")
        self._observers.add(observer_obj)

    def add_handler(self, handler_func):
        pass

