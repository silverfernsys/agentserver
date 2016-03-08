#!/usr/bin/env python
import json
from socket import gethostname
import tornado.httpserver
from db import dal, User, UserAuthToken, Agent
from ws import AgentWSHandler

SERVER_VERSION = '0.0.1a'

class HTTPVersionHandler(tornado.web.RequestHandler):
    @tornado.web.addslash
    def get(self):
        data = {'version': SERVER_VERSION}
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))

# timestamp_str = self.get_query_argument('timestamp', -1.0, True)
# if timestamp_str != None:
#     timestamp = float(timestamp_str)

class HTTPStatusHandler(tornado.web.RequestHandler):
    @tornado.web.addslash
    def get(self):
        try:
            auth_token = self.request.headers.get('authorization')
            token = dal.Session().query(UserAuthToken).filter(UserAuthToken.uuid == auth_token).one()
            data = []
            for agent in dal.Session().query(Agent):
                if agent.ip in AgentWSHandler.IPs():
                    data.append({'agent': agent.ip, 'status': 'online'})
                else:
                    data.append({'agent': agent.ip, 'status': 'offline'})
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


class HTTPTokenHandler(tornado.web.RequestHandler):
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
            else:
                data = {'error': 'invalid username/password'}
        except Exception as e:
            data = {'error': str(e)}
        self.set_header('Content-Type', 'application/json')
        self.write(json.dumps(data))
