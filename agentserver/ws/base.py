#!/usr/bin/env python
# from __future__ import absolute_import
from tornado.escape import json_decode, json_encode
import tornado.websocket


class JSONWebsocket(tornado.websocket.WebSocketHandler):
    invalid_json_error = json_encode(
        {'status': 'error', 'errors': [{'details': 'invalid json'}]})

    def authorize(self, uuid):
        """Override this method."""
        raise NotImplementedError

    def on_json(self, message):
        """Override this method."""
        raise NotImplementedError

    def open(self):
        uuid = self.request.headers.get('authorization')
        if uuid is None or not self.authorize(uuid):
            self.close()

    def on_message(self, message):
        try:
            data = json_decode(message)
            self.on_json(data)
        except ValueError:
            self.write_message(self.invalid_json_error)

    def check_origin(self, origin):
        return True
