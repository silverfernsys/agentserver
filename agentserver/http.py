#!/usr/bin/env python
import json
import tornado.httpserver
from tornado.web import RequestHandler, Finish
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from db import dal, kal, User, UserAuthToken, Agent, AgentDetail, AgentAuthToken

SERVER_VERSION = '0.0.1a'


class HTTPVersionHandler(RequestHandler):
    @tornado.web.addslash
    def get(self):
        data = {'version': SERVER_VERSION}
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPCommandHandler(RequestHandler):
    @tornado.web.addslash
    def post(self):
        print('self.request: %s' % dir(self.request))
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps({'status': 'success'}))


class HTTPStatusHandler(RequestHandler):
    @tornado.web.addslash
    def get(self):
        try:
            auth_token = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == auth_token).one()
            data = []
            # for agent in dal.Session().query(Agent):
            #     if agent.ip in AgentWSHandler.IPs():
            #         data.append({'agent': agent.ip, 'status': 'online'})
            #     else:
            #         data.append({'agent': agent.ip, 'status': 'offline'})
        except Exception as e:
            print('Error: %s' % e)
            try:
                logger = logging.getLogger('Web Server')
                logger.error(e)
            except:
                pass
            data = {'error': 'not authorized'}
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPListHandler(RequestHandler):
    @tornado.web.addslash
    def get(self):
        try:
            auth_token = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == auth_token).one()
            data = []

            for agent in dal.Session().query(Agent):
                data.append({'id': agent.id, 'name': agent.name,
                    'created': agent.created_on.strftime("%Y-%m-%dT%H:%M:%SZ")})
        except Exception as e:
            try:
                logger = logging.getLogger('Web Server')
                logger.error(e)
            except:
                pass
            data = {'error': 'not authorized'}
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPDetailHandler(RequestHandler):
    @tornado.web.addslash
    def post(self):
        try:
            auth_token = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == auth_token).one()
        except Exception as e:
            try:
                logger = logging.getLogger('Web Server')
                logger.error(e)
            except:
                pass
            data = {'error': 'not authorized'}
            status = 403
        try:
            print('REQUEST.BODY: %s' % self.request.body)
            agent_id = tornado.escape.json_decode(self.request.body)['id']
            detail = dal.Session().query(AgentDetail).filter(AgentDetail.agent_id == agent_id).one()
            data = {'hostname': detail.hostname,
                'processor': detail.processor,
                'num_cores': detail.num_cores,
                'memory': detail.memory,
                'dist_name': detail.dist_name,
                'dist_version': detail.dist_version,
                'updated': detail.updated_on.strftime("%Y-%m-%dT%H:%M:%SZ"),
                'created': detail.created_on.strftime("%Y-%m-%dT%H:%M:%SZ")}
            status = 200
        except Exception as e:
            try:
                logger = logging.getLogger('Web Server')
                logger.error(e)
            except:
                pass
            data = {'error': 'invalid id'}
            status = 400
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPDetailCreateUpdateHandler(RequestHandler):
    @tornado.web.addslash
    def post(self):
        session = dal.Session()
        try:
            auth_token = self.request.headers.get('authorization')
            token = session.query(AgentAuthToken).filter(AgentAuthToken.uuid == auth_token).one()
        except Exception as e:
            print('EXCEPTION: %s' % e)
            try:
                logger = logging.getLogger('Web Server')
                logger.error(e)
            except:
                pass
            data = {'status': 'error', 'error_type': 'not authorized'}
            status = 401
        try:
            data = tornado.escape.json_decode(self.request.body)
            detail = token.agent.details
            if detail:
                detail.hostname = data['hostname']
                detail.processor = data['processor']
                detail.num_cores = int(data['num_cores'])
                detail.memory = int(data['memory'])
                detail.dist_name = data['dist_name']
                detail.dist_version = data['dist_version']
                status = 200
            else:
                detail = AgentDetail(agent=token.agent,
                    hostname=data['hostname'],
                    processor=data['processor'],
                    num_cores=int(data['num_cores']),
                    memory=int(data['memory']),
                    dist_name=data['dist_name'],
                    dist_version=data['dist_version'])
                session.add(detail)
                status = 201
            session.commit()
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


class HTTPAgentUpdateHandler(RequestHandler):
    @tornado.web.addslash
    def prepare(self):
        self.session = dal.Session()
        try:
            auth_token = self.request.headers.get('authorization')
            self.token = self.session.query(AgentAuthToken) \
            .filter(AgentAuthToken.uuid == auth_token).one()
            self.agent_id = self.token.agent.id
        except Exception as e:
            print('EXCEPTION: %s' % e)
            try:
                logger = logging.getLogger('Web Server')
                logger.error(e)
            except:
                pass
            data = {'status': 'error', 'error_type': 'not authorized'}
            status = 401
            self.set_status(status)
            self.set_header('Content-Type', 'application/json')
            self.write(json.dumps(data))
            raise Finish()

    def post(self):
        data = tornado.escape.json_decode(self.request.body)['snapshot_update']
        for row in data:
            name = row['name']
            start = datetime.utcfromtimestamp(row['start'])
            for stat in row['stats']:
                msg = {'agent_id': self.agent_id, 'process_name': name,
                    'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    'cpu': stat[1], 'mem': stat[2]}
                kal.connection.send('supervisor', msg)
        kal.connection.flush()
        data = {'status': 'success'}
        status = 200
        self.set_status(status)
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))


class HTTPTokenHandler(RequestHandler):
    @tornado.web.addslash
    def get(self):
        try:
            username = self.request.headers.get('username')
            password = self.request.headers.get('password')
            user = dal.Session().query(User).filter(User.email == username).one()
            if user.authenticates(password):
                try:
                    token = dal.Session().query(UserAuthToken).filter(UserAuthToken.user == user).one()
                except:
                    token = UserAuthToken(user=user)
                    dal.session.add(token)
                    dal.session.commit()
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
