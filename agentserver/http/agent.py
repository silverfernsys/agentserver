from tornado.escape import json_encode
from http.base import JSONHandler
from db.models import Agent, AgentDetail
from db.timeseries import kal
from clients.supervisorclientcoordinator import scc
from utils.validators import snapshot_validator, system_stats_validator
from utils.log import log_auth_error, log_kafka


SNAPSHOT = 'snapshot'


class HTTPAgentHandler(JSONHandler):
    def prepare(self):
        auth_token = self.request.headers.get('authorization')
        self.agent = Agent.authorize(auth_token)
        if self.agent is None:
            log_auth_error(self, auth_token)
            self.send_error(401, message=self.not_authorized_error)
        else:
            super(HTTPAgentHandler, self).prepare()


class HTTPAgentDetailHandler(HTTPAgentHandler):
    success_response_created = json_encode({'status': 'success', 'details': 'detail created'})
    success_response_updated = json_encode({'status': 'success', 'details': 'detail updated'})

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
    snapshot_update_success = json_encode({'status': 'success', 'details': 'snapshot updated'})

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