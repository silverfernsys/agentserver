#! /usr/bin/env python
from time import time
from datetime import datetime
import json
from sqlalchemy.orm.exc import NoResultFound
from db import dal


class SupervisorClient(object):
    def __init__(self, id, ws):
        self.id = id
        self.ip = self.get_ip(ws.request)
        self.ws = ws
        self.session = dal.Session()

    def get_ip(self, request):
        return request.headers.get("X-Real-IP") or request.remote_ip
