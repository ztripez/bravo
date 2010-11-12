import math

from twisted.internet.protocol import Factory
from twisted.internet.task import LoopingCall

from beta.alpha import Entity
from beta.ibeta import IAuthenticator, ITerrainGenerator
from beta.plugin import retrieve_named_plugins
from beta.protocol import AlphaProtocol
from beta.stdio import Console
from beta.world import World

(STATE_UNAUTHENTICATED, STATE_CHALLENGED, STATE_AUTHENTICATED,
    STATE_LOCATED) = range(4)

authenticator_name = "offline"
generator_names = "boring,erosion,grass,safety".split(",")

class AlphaFactory(Factory):

    protocol = AlphaProtocol

    def __init__(self):
        self.world = World("world")
        self.players = set()

        self.entityid = 1
        self.entities = set()

        self.time = 0
        self.time_loop = LoopingCall(self.update_time)
        self.time_loop.start(10)

        self.hooks = {}

        selected = retrieve_named_plugins(IAuthenticator,
            [authenticator_name])[0]

        print "Using authenticator %s" % selected.name
        self.hooks[2] = selected.handshake
        self.hooks[1] = selected.login

        generators = retrieve_named_plugins(ITerrainGenerator,
            generator_names)

        print "Using generators %s" % ", ".join(i.name for i in generators)
        self.world.pipeline = generators

        console = Console()
        console.factory = self

        print "Factory init'd"

    def create_entity(self, x=0, y=0, z=0, entity_type=None):
        self.entityid += 1
        entity = Entity(self.entityid, x, y, z, entity_type)
        self.entities.add(entity)
        return entity

    def destroy_entity(self, entity):
        self.entities.discard(entity)

    def update_time(self):
        self.time += 200
        while self.time > 24000:
            self.time -= 24000

    def broadcast(self, packet):
        for player in self.players:
            player.transport.write(packet)

    def broadcast_for_chunk(self, packet, x, z):
        """
        Broadcast a packet to all players that have a certain chunk loaded.

        `x` and `z` are chunk coordinates, not block coordinates.
        """

        for player in self.players:
            if (x, z) in player.chunks:
                player.transport.write(packet)

    def entities_near(self, x, y, z, radius):
        """
        Given a coordinate and a radius, return all entities within that
        radius of those coordinates.

        All arguments should be in pixels, not blocks.
        """

        return [entity for entity in self.entities
            if math.sqrt((entity.x - x)**2 + (entity.y - y)**2 +
                    (entity.z - z)**2) < radius]
