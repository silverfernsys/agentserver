#!/usr/bin/env python
import json, logging
import tornado.httpserver
from tornado.web import RequestHandler, Finish
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from log import log_kafka
from db import dal, kal, User, UserAuthToken, Agent, AgentDetail, AgentAuthToken
from ws import SupervisorAgentHandler
from clients.supervisorclientcoordinator import scc
from validator import cmd_validator, snapshot_validator, system_stats_validator
from utils import get_ip


SERVER_VERSION = '0.0.1a'
SNAPSHOT = 'snapshot'

class HTTPVersionHandler(RequestHandler):
    response = json.dumps({'version': SERVER_VERSION})
    @tornado.web.addslash
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(self.response)


class UserRequestHandler(RequestHandler):
    error_response = json.dumps({'error': 'not authorized'})
    @tornado.web.addslash
    def prepare(self):
        try:
            auth_token = self.request.headers.get('authorization')
            dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == auth_token).one()
        except Exception as e:
            print('UserRequestHandler.Exception: %s' % e)
            logging.getLogger('Web Server').error(e)
            self.set_status(401)
            self.set_header('Content-Type', 'application/json')
            self.write(self.error_response)
            raise Finish()


class HTTPCommandHandler(UserRequestHandler):
    @tornado.web.addslash
    def post(self):
        try:
            data = json.loads(self.request.body)
            if cmd_validator.validate(data):
                if SupervisorAgentHandler.command(**data):
                    data = {'status': 'success', 'details': 'command {cmd} accepted'.format(cmd=data['cmd'])}
                    status = 200
                else:
                    data = {'status': 'error', 'errors':
                        [{'arg': data['id'], 'details': 'agent not connected'}]}
                    status = 400
            else:
                errors = [{'arg': k, 'details': v} for k, v in cmd_validator.errors.items()]
                data = {'status': 'error', 'errors': errors}
                status = 400
        except ValueError as e:
            data = {'status': 'error', 'errors': [{'details': 'invalid json'}]}
            status = 400
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPListHandler(UserRequestHandler):
    @tornado.web.addslash
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(scc))


class HTTPDetailHandler(UserRequestHandler):
    @tornado.web.addslash
    def post(self):
        self.set_header('Content-Type', 'application/json')
        try:
            agent_id = tornado.escape.json_decode(self.request.body)['id']
            detail = AgentDetail.detail_for_agent_id(agent_id)
            self.write(json.dumps(detail))
        except Exception as e:
            logging.getLogger('Web Server').error(e)
            self.set_status(400)
            self.write(json.dumps({'error': 'invalid id'}))


class HTTPAgentHandler(RequestHandler):
    not_authorized_error = json.dumps({'status': 'error', 'errors': [{'details': 'not authorized'}]})
    invalid_json_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid json'}]})

    def error_message(self, errors):
        errors = [{'arg': k, 'details': v} for k, v in errors.items()]
        return json.dumps({'status': 'error', 'errors': errors})

    @tornado.web.addslash
    def prepare(self):
        self.session = dal.Session()
        try:
            auth_token = self.request.headers.get('authorization')
            self.agent = Agent.authorize(auth_token, self.session)
        except Exception as e:
            logging.getLogger('Web Server').error(e)
            self.set_status(401)
            self.set_header('Content-Type', 'application/json')
            self.write(self.not_authorized_error)
            raise Finish()


class HTTPAgentDetailHandler(HTTPAgentHandler):
    success_response = json.dumps({'status': 'success'})
    @tornado.web.addslash
    def post(self):
        try:
            data = json.loads(self.request.body)
            if system_stats_validator.validate(data):
                created = AgentDetail.update_or_create(self.agent.id, **data)
                if created:
                    status = 201
                else:
                    status = 200
                data = self.success_response
            else:
                status = 400
                data = self.error_message(system_stats_validator.errors)
        except ValueError as e:
            status = 400
            data = self.invalid_json_error
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(data)


class HTTPAgentUpdateHandler(HTTPAgentHandler):
    snapshot_update_success = json.dumps({'status': 'success', 'details': 'snapshot updated'})

    @tornado.web.addslash
    def post(self):
        try:
            data = json.loads(self.request.body)
            if snapshot_validator.validate(data):
                for row in data[SNAPSHOT]:
                    scc.update(self.agent.id, **row)
                    kal.write_stats(self.agent.id, **row)
                    log_kafka(self.agent.id, 'HTTPAgentUpdateHandler', **row)
                status = 200
                data = self.snapshot_update_success
            else:
                status = 400
                data = self.error_message(snapshot_validator.errors)
        except ValueError as e:
            status = 400
            data = self.invalid_json_error
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(data)


class HTTPTokenHandler(RequestHandler):
    authentication_error = json.dumps({'status': 'error', 'errors': [{'details': 'invalid username/password'}]})

    @tornado.web.addslash
    def get(self):
        try:
            session = dal.Session()
            username = self.request.headers.get('username')
            password = self.request.headers.get('password')
            user = session.query(User).filter(User.email == username).one()
            if user.authenticates(password):
                try:
                    token = session.query(UserAuthToken).filter(UserAuthToken.user == user).one()
                except NoResultFound:
                    token = UserAuthToken(user=user)
                    session.add(token)
                    session.commit()
                data = json.dumps({'token': token.uuid})
                status = 200
            else:
                logging.getLogger('HTTPTokenHandler').error('Authentication: incorrect ' \
                    'password for {0} from {1}'.format(username, get_ip(self.request)))
                data = self.authentication_error
                status = 400 # Tornado does not support status code 422: Unprocessable Entity
        except NoResultFound:
            logging.getLogger('HTTPTokenHandler').error('Authentication: unknown ' \
                'username {0} from {1}'.format(username, get_ip(self.request)))
            data = self.authentication_error
            status = 400 # Tornado does not support status code 422: Unprocessable Entity
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(data)
