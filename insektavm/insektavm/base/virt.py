import libvirt
import time

from django.conf import settings

NUM_RETRIES = 3

class VirtError(Exception):
    pass


class ConnectionHandler:
    def __init__(self, libvirt_nodes):
        self.libvirt_nodes = libvirt_nodes
        self._connections = {}

    def __getitem__(self, key):
        try:
            connection_url = self.libvirt_nodes[key]
        except KeyError:
            raise VirtError('No such node')
        if key not in self._connections:
            connection = self.connect(connection_url)
            self._connections[key] = connection

        if self._connections[key].isAlive():
            return self._connections[key]
        else:
            self.invalidate(key)
            connection = self.connect(connection_url)
            self._connections[key] = connection
            return self._connections[key]


    def invalidate(self, key):
        if key in self._connections:
            try:
                self._connections[key].close()
            except libvirt.libvirtError:
                pass
            del self._connections[key]

    def close(self):
        for key in list(self._connections):
            self.invalidate(key)

    def connect(self, connection_url):
        num_tries = 0
        while True:
            try:
                connection = libvirt.open(connection_url)
                return connection
            except libvirt.libvirtError:
                if num_tries < NUM_RETRIES:
                    num_tries += 1
                    time.sleep(1)
                    continue
                else:
                    raise VirtError("Could not connect to...")

connections = ConnectionHandler(settings.LIBVIRT_NODES)
