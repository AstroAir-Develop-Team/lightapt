import selectors
import threading
import time
from ._abnf import ABNF
from ._url import parse_url
from ._core import WebSocket, getdefaulttimeout
from ._exceptions import *

"""
_app.py
websocket - WebSocket client library for Python

Copyright 2022 engn33r

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

__all__ = ["WebSocketApp"]

RECONNECT = 0


def setReconnect(reconnectInterval):
    global RECONNECT
    RECONNECT = reconnectInterval


class DispatcherBase:
    """
    DispatcherBase
    """
    def __init__(self, app, ping_timeout):
        self.app = app
        self.ping_timeout = ping_timeout

    def timeout(self, seconds, callback):
        time.sleep(seconds)
        callback()

    def reconnect(self, seconds, reconnector):
        try:
            while True:
                time.sleep(seconds)
                reconnector(reconnecting=True)
        except KeyboardInterrupt:
            pass


class Dispatcher(DispatcherBase):
    """
    Dispatcher
    """
    def read(self, sock, read_callback, check_callback):
        while self.app.keep_running:
            sel = selectors.DefaultSelector()
            sel.register(self.app.sock.sock, selectors.EVENT_READ)

            r = sel.select(self.ping_timeout)
            if r and not read_callback():
                    break
            check_callback()
            sel.close()


class SSLDispatcher(DispatcherBase):
    """
    SSLDispatcher
    """
    def read(self, sock, read_callback, check_callback):
        while self.app.keep_running:
            r = self.select()
            if r and not read_callback():
                    break
            check_callback()

    def select(self):
        sock = self.app.sock.sock
        if sock.pending():
            return [sock,]

        sel = selectors.DefaultSelector()
        sel.register(sock, selectors.EVENT_READ)

        r = sel.select(self.ping_timeout)
        sel.close()

        if len(r) > 0:
            return r[0][0]


class WrappedDispatcher:
    """
    WrappedDispatcher
    """
    def __init__(self, app, ping_timeout, dispatcher):
        self.app = app
        self.ping_timeout = ping_timeout
        self.dispatcher = dispatcher
        dispatcher.signal(2, dispatcher.abort)  # keyboard interrupt

    def read(self, sock, read_callback, check_callback):
        self.dispatcher.read(sock, read_callback)
        self.ping_timeout and self.timeout(self.ping_timeout, check_callback)

    def timeout(self, seconds, callback):
        self.dispatcher.timeout(seconds, callback)

    def reconnect(self, seconds, reconnector):
        self.timeout(seconds, reconnector)


class WebSocketApp:
    """
    Higher level of APIs are provided. The interface is like JavaScript WebSocket object.
    """

    def __init__(self, url, header=None,
                 on_open=None, on_message=None, on_error=None,
                 on_close=None, on_ping=None, on_pong=None,
                 on_cont_message=None,
                 keep_running=True, get_mask_key=None, cookie=None,
                 subprotocols=None,
                 on_data=None,
                 socket=None):
        self.url = url
        self.header = header if header is not None else []
        self.cookie = cookie

        self.on_open = on_open
        self.on_message = on_message
        self.on_data = on_data
        self.on_error = on_error
        self.on_close = on_close
        self.on_ping = on_ping
        self.on_pong = on_pong
        self.on_cont_message = on_cont_message
        self.keep_running = False
        self.get_mask_key = get_mask_key
        self.sock = None
        self.last_ping_tm = 0
        self.last_pong_tm = 0
        self.subprotocols = subprotocols
        self.prepared_socket = socket
        self.has_errored = False

    def send(self, data, opcode=ABNF.OPCODE_TEXT):

        if not self.sock or self.sock.send(data, opcode) == 0:
            raise WebSocketConnectionClosedException(
                "Connection is already closed.")

    def close(self, **kwargs):
        """
        Close websocket connection.
        """
        self.keep_running = False
        if self.sock:
            self.sock.close(**kwargs)
            self.sock = None

    def _send_ping(self, interval, event, payload):
        while not event.wait(interval):
            self.last_ping_tm = time.time()
            if self.sock:
                try:
                    self.sock.ping(payload)
                except Exception:
                    break

    def run_forever(self, sockopt=None, sslopt=None,
                    ping_interval=0, ping_timeout=None,
                    ping_payload="",
                    http_proxy_host=None, http_proxy_port=None,
                    http_no_proxy=None, http_proxy_auth=None,
                    http_proxy_timeout=None,
                    skip_utf8_validation=False,
                    host=None, origin=None, dispatcher=None,
                    suppress_origin=False, proxy_type=None, reconnect=None):

        if reconnect is None:
            reconnect = RECONNECT

        if ping_timeout is not None and ping_timeout <= 0:
            raise WebSocketException("Ensure ping_timeout > 0")
        if ping_interval is not None and ping_interval < 0:
            raise WebSocketException("Ensure ping_interval >= 0")
        if ping_timeout and ping_interval and ping_interval <= ping_timeout:
            raise WebSocketException("Ensure ping_interval > ping_timeout")
        if not sockopt:
            sockopt = []
        if not sslopt:
            sslopt = {}
        if self.sock:
            raise WebSocketException("socket is already opened")
        thread = None
        self.keep_running = True
        self.last_ping_tm = 0
        self.last_pong_tm = 0

        def teardown(close_frame=None):
            if thread and thread.is_alive():
                event.set()
                thread.join()
            self.keep_running = False
            if self.sock:
                self.sock.close()
            close_status_code, close_reason = self._get_close_args(
                close_frame if close_frame else None)
            self.sock = None

            # Finally call the callback AFTER all teardown is complete
            self._callback(self.on_close, close_status_code, close_reason)

        def setSock(reconnecting=False):
            self.sock = WebSocket(
                self.get_mask_key, sockopt=sockopt, sslopt=sslopt,
                fire_cont_frame=self.on_cont_message is not None,
                skip_utf8_validation=skip_utf8_validation,
                enable_multithread=True)
            self.sock.settimeout(getdefaulttimeout())
            try:
                self.sock.connect(
                    self.url, header=self.header, cookie=self.cookie,
                    http_proxy_host=http_proxy_host,
                    http_proxy_port=http_proxy_port, http_no_proxy=http_no_proxy,
                    http_proxy_auth=http_proxy_auth, http_proxy_timeout=http_proxy_timeout,
                    subprotocols=self.subprotocols,
                    host=host, origin=origin, suppress_origin=suppress_origin,
                    proxy_type=proxy_type, socket=self.prepared_socket)

                self._callback(self.on_open)

                dispatcher.read(self.sock.sock, read, check)
            except (WebSocketConnectionClosedException, ConnectionRefusedError, KeyboardInterrupt, SystemExit, Exception) as e:
                reconnecting or handleDisconnect(e)

        def read():
            if not self.keep_running:
                return teardown()

            try:
                op_code, frame = self.sock.recv_data_frame(True)
            except (WebSocketConnectionClosedException, KeyboardInterrupt) as e:
                if custom_dispatcher:
                    return handleDisconnect(e)
                else:
                    raise e
            if op_code == ABNF.OPCODE_CLOSE:
                return teardown(frame)
            elif op_code == ABNF.OPCODE_PING:
                self._callback(self.on_ping, frame.data)
            elif op_code == ABNF.OPCODE_PONG:
                self.last_pong_tm = time.time()
                self._callback(self.on_pong, frame.data)
            elif op_code == ABNF.OPCODE_CONT and self.on_cont_message:
                self._callback(self.on_data, frame.data,
                               frame.opcode, frame.fin)
                self._callback(self.on_cont_message,
                               frame.data, frame.fin)
            else:
                data = frame.data
                if op_code == ABNF.OPCODE_TEXT:
                    data = data.decode("utf-8")
                self._callback(self.on_data, data, frame.opcode, True)
                self._callback(self.on_message, data)

            return True

        def check():
            if (ping_timeout):
                has_timeout_expired = time.time() - self.last_ping_tm > ping_timeout
                has_pong_not_arrived_after_last_ping = self.last_pong_tm - self.last_ping_tm < 0
                has_pong_arrived_too_late = self.last_pong_tm - self.last_ping_tm > ping_timeout

                if (self.last_ping_tm and
                        has_timeout_expired and
                        (has_pong_not_arrived_after_last_ping or has_pong_arrived_too_late)):
                    raise WebSocketTimeoutException("ping/pong timed out")
            return True

        def handleDisconnect(e):
            self.has_errored = True
            self._callback(self.on_error, e)
            if isinstance(e, SystemExit):
                # propagate SystemExit further
                raise
            if reconnect and not isinstance(e, KeyboardInterrupt):
                dispatcher.reconnect(reconnect, setSock)
            else:
                teardown()

        custom_dispatcher = bool(dispatcher)
        dispatcher = self.create_dispatcher(ping_timeout, dispatcher, parse_url(self.url)[3])

        if ping_interval:
            event = threading.Event()
            thread = threading.Thread(
                target=self._send_ping, args=(ping_interval, event, ping_payload))
            thread.daemon = True
            thread.start()

        setSock()
        return self.has_errored

    def create_dispatcher(self, ping_timeout, dispatcher=None, is_ssl=False):
        if dispatcher:  # If custom dispatcher is set, use WrappedDispatcher
            return WrappedDispatcher(self, ping_timeout, dispatcher)
        timeout = ping_timeout or 10
        if is_ssl:
            return SSLDispatcher(self, timeout)

        return Dispatcher(self, timeout)

    def _get_close_args(self, close_frame):
        """
        _get_close_args extracts the close code and reason from the close body
        if it exists (RFC6455 says WebSocket Connection Close Code is optional)
        """
        # Need to catch the case where close_frame is None
        # Otherwise the following if statement causes an error
        if not self.on_close or not close_frame:
            return [None, None]

        # Extract close frame status code
        if close_frame.data and len(close_frame.data) >= 2:
            close_status_code = 256 * close_frame.data[0] + close_frame.data[1]
            reason = close_frame.data[2:].decode('utf-8')
            return [close_status_code, reason]
        else:
            # Most likely reached this because len(close_frame_data.data) < 2
            return [None, None]

    def _callback(self, callback, *args):
        if callback:
            try:
                callback(self, *args)

            except Exception as e:
                if self.on_error:
                    self.on_error(self, e)
