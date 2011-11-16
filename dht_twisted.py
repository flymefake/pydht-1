from twisted.internet.protocol import DatagramProtocol

from dht import DHTRouter, UDPEndpoint
from bencode import bencode

# This is kind of hacky, but it is entirely twisteds fault for not
# supporting new-type classes.

class ProtocolWrapper(DatagramProtocol):
    def datagramReceived(self, *args, **kwargs):
        self.wrapped.datagramReceived(*args, **kwargs)


class DHTRouterTwisted(DHTRouter):
    def attach_protocol(self, protocol):
        protocol.wrapped = self
        self.protocol = protocol

    @property
    def transport(self):
        return self.protocol.transport

    def send_message(self, endpoint, message):
        self.transport.write(bencode(message), (endpoint.ip, endpoint.port))

    def datagramReceived(self, data, (host, port)):
        self.process_message(UDPEndpoint(host, port), data)



