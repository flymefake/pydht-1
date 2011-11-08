from twisted.internet import reactor

from dht_twisted import DHTRouterTwisted, ProtocolWrapper
from dht import DHTRouter, UDPEndpoint


dht_router = DHTRouterTwisted(9999)
proto_wrapper = ProtocolWrapper()
dht_router.attach_protocol(proto_wrapper)

def add_node():
    dht_router.bootstrap_with_endpoint(UDPEndpoint('69.56.173.11', 7681))
    # dht_router.bootstrap_with_endpoint(UDPEndpoint('216.65.165.221', 23423))

reactor.callLater(2, add_node)
reactor.listenUDP(9999, proto_wrapper)
reactor.run()
