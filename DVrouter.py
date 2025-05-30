####################################################
# DVrouter.py
# Name: <tran gia khanh>
# HUID: <23021600>
####################################################

from router import Router
from packet import Packet
import json

class DVrouter(Router):
    """Distance vector routing protocol implementation."""

    def __init__(self, addr, heartbeat_time):
        # Initialize base class (DO NOT REMOVE)
        super().__init__(addr)
        # How often to broadcast our distance vector (ms)
        self.heartbeat_time = heartbeat_time
        self.last_time = 0
        # Infinity cost for count-to-infinity prevention
        self.INFINITY = 16
        # port -> cost of direct link
        self.neighbors = {}
        # port -> neighbor router address
        self.port2nbr = {}
        # neighbor address -> last advertised distance vector
        self.neighbor_vectors = {}
        # our current distance vector: dest_addr -> cost
        self.distance_vector = {self.addr: 0}
        # forwarding table: dest_addr -> port
        self.forwarding_table = {}

    def broadcast_vector(self):
        """Broadcast our distance vector to all neighbors."""
        content = json.dumps(self.distance_vector)
        for port in self.neighbors:
            p = Packet(kind=Packet.ROUTING,
                       src_addr=self.addr,
                       dst_addr=None,
                       content=content)
            self.send(port, p)

    def recompute_and_update(self):
        """
        Recompute distance vector and forwarding table from scratch.
        Returns True if either changed.
        """
        new_dv = {self.addr: 0}
        new_ft = {}
        # 1) direct neighbors
        for port, cost in self.neighbors.items():
            nbr = self.port2nbr[port]
            if cost < new_dv.get(nbr, self.INFINITY + 1):
                new_dv[nbr] = cost
                new_ft[nbr] = port
        # 2) via neighbors' advertised vectors
        for port, cost in self.neighbors.items():
            nbr = self.port2nbr[port]
            vec = self.neighbor_vectors.get(nbr, {})
            for dest, dist in vec.items():
                if dest == self.addr:
                    continue
                new_cost = min(self.INFINITY, cost + dist)
                if new_cost < new_dv.get(dest, self.INFINITY + 1):
                    new_dv[dest] = new_cost
                    new_ft[dest] = port
        # 3) detect changes
        if new_dv != self.distance_vector or new_ft != self.forwarding_table:
            self.distance_vector = new_dv
            self.forwarding_table = new_ft
            return True
        return False

    def handle_packet(self, port, packet):
        if packet.is_traceroute:
            # Forward data packet based on forwarding table
            dst = packet.dst_addr
            if dst in self.forwarding_table:
                self.send(self.forwarding_table[dst], packet)
        else:
            # Routing packet: update neighbor's vector
            recd = json.loads(packet.content)
            nbr = packet.src_addr
            self.neighbor_vectors[nbr] = recd
            # Recompute and broadcast if changed
            if self.recompute_and_update():
                self.broadcast_vector()

    def handle_new_link(self, port, endpoint, cost):
        # Add new neighbor link
        self.neighbors[port] = cost
        self.port2nbr[port] = endpoint
        # Consider direct route
        if cost < self.distance_vector.get(endpoint, self.INFINITY + 1):
            self.distance_vector[endpoint] = cost
            self.forwarding_table[endpoint] = port
        if self.recompute_and_update():
            self.broadcast_vector()

    def handle_remove_link(self, port):
        # Remove neighbor link
        if port in self.neighbors:
            nbr = self.port2nbr.pop(port)
            self.neighbors.pop(port)
            self.neighbor_vectors.pop(nbr, None)
            if self.recompute_and_update():
                self.broadcast_vector()

    def handle_time(self, time_ms):
        # Periodic broadcast
        if time_ms - self.last_time >= self.heartbeat_time:
            self.last_time = time_ms
            self.broadcast_vector()

    def __repr__(self):
        # Debug representation (not graded)
        return f"DVrouter(addr={self.addr}, dv={self.distance_vector}, ft={self.forwarding_table})"