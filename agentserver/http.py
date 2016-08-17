#!/usr/bin/env python
import json, logging
import tornado.httpserver
from tornado.web import RequestHandler, Finish
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from db import dal, kal, User, UserAuthToken, Agent, AgentDetail, AgentAuthToken
from clients.supervisorclientcoordinator import scc

SERVER_VERSION = '0.0.1a'


class HTTPVersionHandler(RequestHandler):
    @tornado.web.addslash
    def get(self):
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({'version': SERVER_VERSION}))


class UserRequestHandler(RequestHandler):
    @tornado.web.addslash
    def prepare(self):
        try:
            auth_token = self.request.headers.get('authorization')
            dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == auth_token).one()
        except Exception as e:
            logging.getLogger('Web Server').error(e)
            self.set_status(401)
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps({'error': 'not authorized'}))
            raise Finish()


class HTTPCommandHandler(UserRequestHandler):
    @tornado.web.addslash
    def post(self):
        print('******self.request: %s' % dir(self.request))
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({'status': 'success'}))


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
            self.write(json.dumps({'status': 'error', 'error_type': 'not authorized'}))
            raise Finish()


class HTTPAgentDetailHandler(HTTPAgentHandler):
    @tornado.web.addslash
    def post(self):
        try:
            data = tornado.escape.json_decode(self.request.body)
            detail = self.agent.details
            if detail:
                detail.hostname = data['hostname']
                detail.processor = data['processor']
                detail.num_cores = int(data['num_cores'])
                detail.memory = int(data['memory'])
                detail.dist_name = data['dist_name']
                detail.dist_version = data['dist_version']
                status = 200
            else:
                detail = AgentDetail(agent=self.agent,
                    hostname=data['hostname'],
                    processor=data['processor'],
                    num_cores=int(data['num_cores']),
                    memory=int(data['memory']),
                    dist_name=data['dist_name'],
                    dist_version=data['dist_version'])
                self.session.add(detail)
                status = 201
            self.session.commit()
            data = {'status': 'success'}
        except KeyError as e:
            status = 400
            data = {'status': 'error', 'error_type': 'missing value', 'value': str(e)} 
        except ValueError as e:
            status = 400
            data = {'status': 'error', 'error_type': 'value error', 'value': str(e)}
        except Exception as e:
            status = 400
            data = {'status': 'error', 'error_type': 'general error', 'value': str(e)}
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPAgentUpdateHandler(HTTPAgentHandler):
    @tornado.web.addslash
    def post(self):
        data = tornado.escape.json_decode(self.request.body)['snapshot_update']
        for row in data:
            name = row['name']
            start = datetime.utcfromtimestamp(row['start'])
            for stat in row['stats']:
                msg = {'agent_id': self.agent.id, 'process_name': name,
                    'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    'cpu': stat[1], 'mem': stat[2]}
                kal.connection.send('supervisor', msg)
        kal.connection.flush()
        self.set_status(200)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({'status': 'success'}))


class HTTPTokenHandler(RequestHandler):
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
                except:
                    token = UserAuthToken(user=user)
                    session.add(token)
                    session.commit()
                data = {'token': token.uuid}
                status = 200
            else:
                data = {'error': 'invalid username/password'}
                status = 400 # Tornado does not support status code 422: Unprocessable Entity
        except NoResultFound:
                data = {'error': 'invalid username/password'}
                status = 400 # Tornado does not support status code 422: Unprocessable Entity
        except Exception as e:
            data = {'error': str(e)}
            status = 400
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))
