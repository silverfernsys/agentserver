import base64
import collections
import os

from tornado.concurrent import Future
from tornado import simple_httpclient, httpclient
from tornado.concurrent import TracebackFuture
from tornado.ioloop import IOLoop
from tornado.tcpclient import TCPClient
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.web import Application
from tornado.websocket import WebSocketProtocol13

class WebSocketClientConnection(simple_httpclient._HTTPConnection):
    """WebSocket client connection.
    This class should not be instantiated directly; use the
    `websocket_connect` function instead.
    """
    def __init__(self, io_loop, request, headers=None, on_message_callback=None,
                 compression_options=None):
        self.compression_options = compression_options
        self.connect_future = TracebackFuture()
        self.protocol = None
        self.read_future = None
        self.read_queue = collections.deque()
        self.key = base64.b64encode(os.urandom(16))
        self._on_message_callback = on_message_callback
        self.close_code = self.close_reason = None

        scheme, sep, rest = request.url.partition(':')
        scheme = {'ws': 'http', 'wss': 'https'}[scheme]
        request.url = scheme + sep + rest
        request.headers.update({
            'Upgrade': 'websocket',
            'Connection': 'Upgrade',
            'Sec-WebSocket-Key': self.key,
            'Sec-WebSocket-Version': '13',
        })

        if headers != None:
            request.headers.update(headers)

        if self.compression_options is not None:
            # Always offer to let the server set our max_wbits (and even though
            # we don't offer it, we will accept a client_no_context_takeover
            # from the server).
            # TODO: set server parameters for deflate extension
            # if requested in self.compression_options.
            request.headers['Sec-WebSocket-Extensions'] = (
                'permessage-deflate; client_max_window_bits')

        self.tcp_client = TCPClient(io_loop=io_loop)
        super(WebSocketClientConnection, self).__init__(
            io_loop, None, request, lambda: None, self._on_http_response,
            104857600, self.tcp_client, 65536, 104857600)

    def close(self, code=None, reason=None):
        """Closes the websocket connection.
        ``code`` and ``reason`` are documented under
        `WebSocketHandler.close`.
        .. versionadded:: 3.2
        .. versionchanged:: 4.0
           Added the ``code`` and ``reason`` arguments.
        """
        if self.protocol is not None:
            self.protocol.close(code, reason)
            self.protocol = None

    def on_connection_close(self):
        if not self.connect_future.done():
            self.connect_future.set_exception(StreamClosedError())
        self.on_message(None)
        self.tcp_client.close()
        super(WebSocketClientConnection, self).on_connection_close()

    def _on_http_response(self, response):
        if not self.connect_future.done():
            if response.error:
                self.connect_future.set_exception(response.error)
            else:
                self.connect_future.set_exception(WebSocketError(
                    "Non-websocket response"))

    def headers_received(self, start_line, headers):
        if start_line.code != 101:
            return super(WebSocketClientConnection, self).headers_received(
                start_line, headers)

        self.headers = headers
        self.protocol = self.get_websocket_protocol()
        self.protocol._process_server_headers(self.key, self.headers)
        self.protocol._receive_frame()

        if self._timeout is not None:
            self.io_loop.remove_timeout(self._timeout)
            self._timeout = None

        self.stream = self.connection.detach()
        self.stream.set_close_callback(self.on_connection_close)
        # Once we've taken over the connection, clear the final callback
        # we set on the http request.  This deactivates the error handling
        # in simple_httpclient that would otherwise interfere with our
        # ability to see exceptions.
        self.final_callback = None

        self.connect_future.set_result(self)

    def write_message(self, message, binary=False):
        """Sends a message to the WebSocket server."""
        return self.protocol.write_message(message, binary)

    def read_message(self, callback=None):
        """Reads a message from the WebSocket server.
        If on_message_callback was specified at WebSocket
        initialization, this function will never return messages
        Returns a future whose result is the message, or None
        if the connection is closed.  If a callback argument
        is given it will be called with the future when it is
        ready.
        """
        assert self.read_future is None
        future = TracebackFuture()
        if self.read_queue:
            future.set_result(self.read_queue.popleft())
        else:
            self.read_future = future
        if callback is not None:
            self.io_loop.add_future(future, callback)
        return future

    def on_message(self, message):
        if self._on_message_callback:
            self._on_message_callback(message)
        elif self.read_future is not None:
            self.read_future.set_result(message)
            self.read_future = None
        else:
            self.read_queue.append(message)

    def on_pong(self, data):
        pass

    def get_websocket_protocol(self):
        return WebSocketProtocol13(self, mask_outgoing=True,
                                   compression_options=self.compression_options)


def websocket_connect(url, headers=None, io_loop=None, callback=None, connect_timeout=None,
                      on_message_callback=None, compression_options=None):
    """Client-side websocket support.
    Takes a url and returns a Future whose result is a
    `WebSocketClientConnection`.
    ``compression_options`` is interpreted in the same way as the
    return value of `.WebSocketHandler.get_compression_options`.
    The connection supports two styles of operation. In the coroutine
    style, the application typically calls
    `~.WebSocketClientConnection.read_message` in a loop::
        conn = yield websocket_connect(url)
        while True:
            msg = yield conn.read_message()
            if msg is None: break
            # Do something with msg
    In the callback style, pass an ``on_message_callback`` to
    ``websocket_connect``. In both styles, a message of ``None``
    indicates that the connection has been closed.
    .. versionchanged:: 3.2
       Also accepts ``HTTPRequest`` objects in place of urls.
    .. versionchanged:: 4.1
       Added ``compression_options`` and ``on_message_callback``.
       The ``io_loop`` argument is deprecated.
    """
    if io_loop is None:
        io_loop = IOLoop.current()
    if isinstance(url, httpclient.HTTPRequest):
        assert connect_timeout is None
        request = url
        # Copy and convert the headers dict/object (see comments in
        # AsyncHTTPClient.fetch)
        request.headers = httputil.HTTPHeaders(request.headers)
    else:
        request = httpclient.HTTPRequest(url, connect_timeout=connect_timeout)
    request = httpclient._RequestProxy(request, httpclient.HTTPRequest._DEFAULTS)
    conn = WebSocketClientConnection(io_loop, request, headers=headers,
                                     on_message_callback=on_message_callback,
                                     compression_options=compression_options)
    if callback is not None:
        io_loop.add_future(conn.connect_future, callback)
    return conn.connect_future
