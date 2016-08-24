#!/usr/bin/env python
import json, logging
import tornado.httpserver
from tornado.web import RequestHandler, Finish
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from log import log_kafka
from db import (dal, kal, User, UserAuthToken, Agent, AgentDetail,
    AgentAuthToken, UserAuthenticationException)
from ws import SupervisorAgentHandler
from clients.supervisorclientcoordinator import scc
from validator import cmd_validator, snapshot_validator, system_stats_validator
from utils import get_ip


SERVER_VERSION = '0.0.1a'
SNAPSHOT = 'snapshot'

class JsonHandler(RequestHandler):
    invalid_json_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid json'}]})
    invalid_http_method_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid http method'}]})
    unknown_error = json.dumps({'status': 'error', 'errors': [{'details': 'unknown error'}]})

    def prepare(self):
        if self.request.body:
            try:
                json_data = tornado.escape.json_decode(self.request.body)
                self.json = json_data
            except ValueError:
                self.send_error(400, message=self.invalid_json_error) # Bad Request

    def set_default_headers(self):
        self.set_header('Content-Type', 'application/json')

    def write_error(self, status_code, **kwargs):
        if 'message' not in kwargs:
            if status_code == 405:
                kwargs['message'] = self.invalid_http_method_error
            else:
                kwargs['message'] = self.unknown_error

        self.write(kwargs['message'])


class HTTPVersionHandler(JsonHandler):
    response = json.dumps({'version': SERVER_VERSION})
    @tornado.web.addslash
    def get(self):
        self.write(self.response)


class BadTokenLogger(object):
    def log(self, auth_token):
        if auth_token:
            logging.getLogger(self.__class__.__name__).error('Request with invalid token "{0}" ' \
                'from {1}'.format(auth_token, get_ip(self.request)))
        else:
            logging.getLogger(self.__class__.__name__).error('Request with missing token ' \
                'from {0}'.format(get_ip(self.request)))


class CommonRequestHandler(JsonHandler):
    not_authorized_error = json.dumps({'status': 'error', 'errors': [{'details': 'not authorized'}]})

    def error_message(self, errors):
        errors = [{'arg': k, 'details': v} for k, v in errors.items()]
        return json.dumps({'status': 'error', 'errors': errors})


class UserRequestHandler(CommonRequestHandler, BadTokenLogger):
    def prepare(self):
        try:
            auth_token = self.request.headers.get('authorization')
            UserAuthToken.authorize(auth_token)
        except NoResultFound:
            self.log(auth_token)
            self.send_error(401, message=self.not_authorized_error)
        super(UserRequestHandler, self).prepare()


class HTTPCommandHandler(UserRequestHandler):
    @classmethod
    def cmd_success(cls, cmd):
        return json.dumps({'status': 'success',
            'details': 'command {0} accepted'.format(cmd)})

    @classmethod
    def cmd_error(cls, id):
        return json.dumps({'status': 'error', 'errors':
            [{'arg': id, 'details': 'agent not connected'}]})

    @tornado.web.addslash
    def post(self):
        if cmd_validator.validate(self.json):
            if SupervisorAgentHandler.command(**self.json):
                data = self.cmd_success(self.json['cmd'])
                status = 200
            else:
                data = self.cmd_error(self.json['id'])
                status = 400
        else:
            data = self.error_message(cmd_validator.errors)
            status = 400
        self.set_status(status)
        self.write(data)


class HTTPListHandler(UserRequestHandler):
    @tornado.web.addslash
    def get(self):
        self.write(json.dumps(scc))


class HTTPDetailHandler(UserRequestHandler):
    invalid_id_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid id'}]})

    @tornado.web.addslash
    def post(self):
        try:
            detail = AgentDetail.detail_for_agent_id(self.json['id'])
            status = 200
            data = json.dumps(detail)
        except NoResultFound as e:
            status = 400
            data = self.invalid_id_error
        self.set_status(status)
        self.write(data)


class HTTPAgentHandler(CommonRequestHandler, BadTokenLogger):
    def prepare(self):
        try:
            auth_token = self.request.headers.get('authorization')
            self.agent = Agent.authorize(auth_token)
        except Exception as e:
            self.log(auth_token)
            self.send_error(401, message=self.not_authorized_error)
        super(HTTPAgentHandler, self).prepare()


class HTTPAgentDetailHandler(HTTPAgentHandler):
    success_response_created = json.dumps({'status': 'success', 'details': 'detail created'})
    success_response_updated = json.dumps({'status': 'success', 'details': 'detail updated'})

    @tornado.web.addslash
    def post(self):
        if system_stats_validator.validate(self.json):
            created = AgentDetail.update_or_create(self.agent.id, **self.json)
            if created:
                status = 201
                data = self.success_response_created
            else:
                status = 200
                data = self.success_response_updated
        else:
            status = 400
            data = self.error_message(system_stats_validator.errors)
        self.set_status(status)
        self.write(data)


class HTTPAgentUpdateHandler(HTTPAgentHandler):
    snapshot_update_success = json.dumps({'status': 'success', 'details': 'snapshot updated'})

    @tornado.web.addslash
    def post(self):
        if snapshot_validator.validate(self.json):
            for row in self.json[SNAPSHOT]:
                scc.update(self.agent.id, **row)
                kal.write_stats(self.agent.id, **row)
                log_kafka(self.agent.id, 'HTTPAgentUpdateHandler', **row)
            status = 200
            data = self.snapshot_update_success
        else:
            status = 400
            data = self.error_message(snapshot_validator.errors)
        self.set_status(status)
        self.write(data)


class HTTPTokenHandler(JsonHandler):
    authentication_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid username/password'}]})

    @tornado.web.addslash
    def get(self):
        try:
            username = self.request.headers.get('username')
            password = self.request.headers.get('password')
            token = User.authenticate(username, password)
            data = json.dumps({'token': token})
            status = 200
        except UserAuthenticationException as e:
            logging.getLogger('HTTPTokenHandler').error('Authentication: {0} ' \
                '{1} from {2}'.format(e.message, username, get_ip(self.request)))
            data = self.authentication_error
            status = 400 # Tornado does not support status code 422: Unprocessable Entity
        self.set_status(status)
        self.write(data)
