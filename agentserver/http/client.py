from tornado.escape import json_encode
from http.base import JSONHandler
from db.models import User, AgentDetail, UserAuthenticationException 
from ws.agent import SupervisorAgentHandler
from clients.supervisorclientcoordinator import scc
from utils.validators import cmd_validator
from utils.log import log_auth_error, log_authentication_error


SERVER_VERSION = '0.0.1a'


class HTTPVersionHandler(JSONHandler):
    response = json_encode({'version': SERVER_VERSION})

    def get(self):
        self.write(self.response)


class UserRequestHandler(JSONHandler):
    def prepare(self):
        auth_token = self.request.headers.get('authorization')
        if not User.authorize(auth_token):
            log_auth_error(self, auth_token)
            self.send_error(401, message=self.not_authorized_error)
        else:
            super(UserRequestHandler, self).prepare()


class HTTPCommandHandler(UserRequestHandler):
    @classmethod
    def cmd_success(cls, cmd):
        return json_encode({'status': 'success',
            'details': 'command {0} accepted'.format(cmd)})

    @classmethod
    def cmd_error(cls, id):
        return json_encode({'status': 'error', 'errors':
            [{'arg': id, 'details': 'agent not connected'}]})

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
    def get(self):
        self.write(json_encode(scc))


class HTTPDetailHandler(UserRequestHandler):
    invalid_id_error = json_encode({'status': 'error', 'errors': [{'details': 'invalid id'}]})

    def post(self):
        detail = AgentDetail.detail_for_agent_id(self.json['id'])
        if detail:
            status = 200
            data = json_encode(detail)
        else:
            status = 400
            data = self.invalid_id_error
        self.set_status(status)
        self.write(data)


class HTTPTokenHandler(JSONHandler):
    authentication_error = json_encode({'status': 'error', 'errors': [{'details': 'invalid username/password'}]})

    def get(self):
        try:
            username = self.request.headers.get('username')
            password = self.request.headers.get('password')
            token = User.authenticate(username, password)
            data = json_encode({'token': token})
            status = 200
        except UserAuthenticationException as e:
            log_authentication_error(self, e.message, username)
            data = self.authentication_error
            status = 400 # Tornado does not support status code 422: Unprocessable Entity
        self.set_status(status)
        self.write(data)