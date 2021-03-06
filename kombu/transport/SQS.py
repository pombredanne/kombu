
"""
kombu.transport.SQS
===================

Amazon SQS transport.

:copyright: (c) 2010 - 2011 by Ask Solem
:license: BSD, see LICENSE for more details.

"""
import socket
import string

from Queue import Empty

from anyjson import serialize, deserialize
from boto import exception
from boto.sqs.connection import SQSConnection
from boto.sqs.message import Message

from kombu.transport import virtual
from kombu.utils import cached_property


# dots are replaced by dash, all other punctuation
# replaced by underscore.
CHARS_REPLACE = string.punctuation.replace('-', '') \
                                  .replace('_', '') \
                                  .replace('.', '')
CHARS_REPLACE_TABLE = string.maketrans(CHARS_REPLACE + '.',
                                       "_" * len(CHARS_REPLACE) + '-')


class Channel(virtual.Channel):
    _client = None

    def entity_name(self, name, table=CHARS_REPLACE_TABLE):
        return name.translate(table)

    def _new_queue(self, queue, **kwargs):
        return self.client.create_queue(self.entity_name(queue),
                                        self.visibility_timeout)

    def _get(self, queue):
        q = self._new_queue(queue)
        rs = q.get_messages(1)
        if rs:
            return deserialize(rs[0].get_body())
        raise Empty()

    def _size(self, queue):
        return self._new_queue(queue).count()

    def _put(self, queue, message, **kwargs):
        q = self._new_queue(queue)
        m = Message()
        m.set_body(serialize(message))
        q.write(m)

    def _purge(self, queue):
        q = self._new_queue(queue)
        size = q.count()
        q.clear()
        return size

    def close(self):
        super(Channel, self).close()
        if self._client:
            try:
                self._client.close()
            except AttributeError, exc:  # FIXME ???
                if "can't set attribute" not in str(exc):
                    raise

    def _open(self):
        conninfo = self.connection.client
        return SQSConnection(conninfo.userid, conninfo.password)

    @property
    def client(self):
        if self._client is None:
            self._client = self._open()
        return self._client

    @cached_property
    def visibility_timeout(self):
        options = self.connection.client.transport_options
        return options.get("visibility_timeout")


class Transport(virtual.Transport):
    Channel = Channel

    interval = 1
    default_port = None
    connection_errors = (exception.SQSError,
                         socket.error)
    channel_errors = (exception.SQSDecodeError, )
