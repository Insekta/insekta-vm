import libvirt

from django.conf import settings


class VirtError(Exception):
    pass


class ConnectionHandler:
    def __init__(self, libvirt_nodes):
        self.libvirt_nodes = libvirt_nodes
        self._connections = {}

    def __getitem__(self, key):
        if key not in self._connections:
            try:
                connection_url = self.libvirt_nodes[key]
            except KeyError:
                raise VirtError('No such node')
            connection = libvirt.open(connection_url)
            self._connections[key] = connection

        return self._connections[key]

    def close(self):
        for key, conn in self._connections.items():
            conn.close()
            del self._connections[key]


connections = ConnectionHandler(settings.LIBVIRT_NODES)
