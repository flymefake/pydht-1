import dht
from dht import DHTRouter, DHTNode, UDPEndpoint
import unittest
import os

class TestDHTNodeID(unittest.TestCase):
    def setUp(self):
        pass

    def test_bytea_constructor(self):
        some_bytea = os.urandom(20)
        self.assertEqual(dht.DHTNodeID.from_bytea(some_bytea).to_bin(), some_bytea)

    def test_copy_constructor(self):
        dht_node = dht.DHTNodeID.from_bytea(os.urandom(20))
        self.assertEqual(dht.DHTNodeID(dht_node), dht_node)

    def test_numeric_constructor(self):
        dht_node_id = 857505334070830689182859575115226779801267384433
        self.assertEqual(dht_node_id, int(dht.DHTNodeID(dht_node_id)))

    def test_equality(self):
        dht_node_id = 1279565159797386125088075387977303339237112894825
        self.assertEqual(dht.DHTNodeID(dht_node_id), dht.DHTNodeID(dht_node_id))

    def test_distance(self):
        a = dht.DHTNodeID(502355916696019766840671334776071591198461867758)
        b = dht.DHTNodeID(1082512638303256836540936677183999661957895165058)
        c = dht.DHTNodeID(1338131191610747777876268209261487259116956099180)
        null_node = dht.DHTNodeID(0)

        self.assertEqual(a.distance(a), null_node)
        self.assertEqual(a.distance(c), b)
        self.assertEqual(a.distance(b), c)
        self.assertEqual(a.distance(null_node), a)
        self.assertEqual(b.distance(a), c)
        self.assertEqual(b.distance(b), null_node)
        self.assertEqual(b.distance(c), a)
        self.assertEqual(b.distance(null_node), b)
        self.assertEqual(c.distance(b), a)
        self.assertEqual(c.distance(a), b)
        self.assertEqual(c.distance(c), null_node)
        self.assertEqual(c.distance(null_node), c)


class TestDHTNode(unittest.TestCase):
    def setUp(self):
        pass


class TestDHTRouter(unittest.TestCase):
    def setUp(self):
        pass


if __name__ == '__main__':
    unittest.main()
