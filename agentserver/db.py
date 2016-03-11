import re
from datetime import datetime

from sqlalchemy import (Column, Integer, Numeric, String, DateTime, ForeignKey,
                        Boolean, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, validates

from sqlalchemy.event import listen

from influxdb import InfluxDBClient 

from passlib.apps import custom_app_context as pwd_context

from utils import uuid


Base = declarative_base()


class Agent(Base):
    __tablename__ = 'agents'

    id = Column(Integer(), primary_key=True)
    ip = Column(String(), nullable=False, unique=True)
    retention_policy = Column(String(), nullable=False)
    timeseries_database_name = Column(String(), nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    @classmethod
    def supervisor_database_name(self, ip):
        return 'supervisor_%s' % ip.replace('.', '_')

    @validates('retention_policy')
    def validate_retention_policy(self, key, policy):
        regex = re.compile('\d+[mhdw]$|^INF$')
        result = regex.match(policy)
        assert result != None
        return policy

    def __repr__(self):
        return "Agent(ip='{self.ip}', " \
            "retention_policy='{self.retention_policy}', " \
            "timeseries_database_name='{self.timeseries_database_name}', " \
            "created_on='{self.created_on}'".format(self=self)


class AgentDetail(Base):
    __tablename__ = 'agentdetails'

    id = Column(Integer(), primary_key=True)
    agent_id = Column(Integer(), ForeignKey('agents.id'), unique=True)
    num_cores = Column(Integer(), default=1)
    memory = Column(Integer(), default=0)
    os_version = Column(String(), nullable=False)
    hostname = Column(String, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    agent = relationship("Agent", backref=backref('details', uselist=False))

    def __repr__(self):
        return "UserAuthToken(agent_id='{self.agent_id}', " \
            "num_cores='{self.num_cores}', " \
            "memory='{self.memory}', " \
            "os_version='{self.os_version}', " \
            "hostname='{self.hostname}', " \
            "created_on='{self.created_on}'".format(self=self)


class AgentAuthToken(Base):
    __tablename__ = 'agentauthtokens'

    uuid = Column(String(), primary_key=True, default=uuid)
    agent_id = Column(Integer(), ForeignKey('agents.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    agent = relationship("Agent", backref=backref('token', uselist=False))

    def __repr__(self):
        return "UserAuthToken(uuid='{self.uuid}', " \
            "agent_id='{self.agent_id}', " \
            "created_on='{self.created_on}'".format(self=self)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)
    email = Column(String(), nullable=False, unique=True)
    password = Column(String(), nullable=False)
    is_admin = Column(Boolean(), default=False)
    created_on = Column(DateTime(), default=datetime.now)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)

    def authenticates(self, other_password):
        try:
            return pwd_context.verify(other_password, self.password)
        except:
            return False

    def __repr__(self):
        return "User(name='{self.name}', " \
            "email='{self.email}', " \
            "is_admin='{self.is_admin}', " \
            "password='{self.password}')".format(self=self)

def hash_password(target, value, oldvalue, initiator):
    "hashes password"
    return pwd_context.encrypt(value)

listen(User.password, 'set', hash_password, retval=True)


class UserAuthToken(Base):
    __tablename__ = 'userauthtokens'

    uuid = Column(String(), primary_key=True, default=uuid)
    user_id = Column(Integer(), ForeignKey('users.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    user = relationship("User", backref=backref('token', uselist=False))

    def __repr__(self):
        return "UserAuthToken(uuid='{self.uuid}', " \
            "user_id='{self.user_id}', " \
            "created_on='{self.created_on}'".format(self=self)  

# class Cookie(Base):
#     __tablename__ = 'cookies'

#     cookie_id = Column(Integer, primary_key=True)
#     cookie_name = Column(String(50), index=True)
#     cookie_recipe_url = Column(String(255))
#     cookie_sku = Column(String(55))
#     quantity = Column(Integer())
#     unit_cost = Column(Numeric(12, 2))

#     def __repr__(self):
#         return "Cookie(cookie_name='{self.cookie_name}', " \
#             "cookie_recipe_url='{self.cookie_recipe_url}', " \
#             "cookie_sku='{self.cookie_sku}', " \
#             "quantity={self.quantity}, " \
#             "unit_cost={self.unit_cost})".format(self=self)


# class Order(Base):
#     __tablename__ = 'orders'
#     order_id = Column(Integer(), primary_key=True)
#     user_id = Column(Integer(), ForeignKey('users.id'))
#     shipped = Column(Boolean(), default=False)

#     user = relationship("User", backref=backref('orders', order_by=order_id))

#     def __repr__(self):
#         return "Order(user_id={self.user_id}, " \
#             "shipped={self.shipped})".format(self=self)


# class LineItem(Base):
#     __tablename__ = 'line_items'
#     line_item_id = Column(Integer(), primary_key=True)
#     order_id = Column(Integer(), ForeignKey('orders.order_id'))
#     cookie_id = Column(Integer(), ForeignKey('cookies.cookie_id'))
#     quantity = Column(Integer())
#     extended_cost = Column(Numeric(12, 2))

#     order = relationship("Order", backref=backref('line_items',
#                                                   order_by=line_item_id))
#     cookie = relationship("Cookie", uselist=False)

#     def __repr__(self):
#         return "LineItems(order_id={self.order_id}, " \
#             "cookie_id={self.cookie_id}, " \
#             "quantity={self.quantity}, " \
#             "extended_cost={self.extended_cost})".format(
#                 self=self)


class DataAccessLayer:

    def __init__(self):
        self.engine = None
        self.Session = None
        self.conn_string = None

    def connect(self, conn_string=None):
        self.conn_string = conn_string
        if self.conn_string:
            self.engine = create_engine(self.conn_string)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)


dal = DataAccessLayer()

class TimeseriesAccessLayer(object):
    def __init__(self):
        self.connections = {}

    def connect(self, uri, dbname):
        (username, password, host, port) = self._parseTimeseriesURI(uri)
        client = InfluxDBClient(host, port, username, password, dbname)
        self.connections[dbname] = client

    def connection(self, dbname):
        if dbname in self.connections:
            return self.connections[dbname]
        else:
            return None

    def _parseTimeseriesURI(self, uri):
        split_uri = uri.split('://')
        if split_uri[0] == 'influxdb':
            up_hp = split_uri[1].split('@')
            username = up_hp[0].split(':')[0]
            password = up_hp[0].split(':')[1]
            host = up_hp[1].split(':')[0]
            port = up_hp[1].split(':')[1]
            return (username, password, host, port)
        else:
            return (None, None, None, None)

tal = TimeseriesAccessLayer()


def prep_db(session):
    print('db.py preb_db')
    # Generate users
    user_0 = User(name='Marc Wilson',
                     email='marcw@silverfern.io',
                     is_admin=True,
                     password='asdf')
    user_1 = User(name='Phil Lake',
                     email='philip@gmail.com',
                     is_admin=False,
                     password='asdf')
    user_2 = User(name='Colin Ng',
                     email='colin@ngland.net',
                     is_admin=True,
                     password='asdf')
    # session.bulk_save_objects([user_0, user_1, user_2])
    # session.commit()

    # Generate user tokens
    u_token_0 = UserAuthToken(user=user_0)
    u_token_1 = UserAuthToken(user=user_1)
    u_token_2 = UserAuthToken(user=user_2)
    session.add(u_token_0)
    session.add(u_token_1)
    session.add(u_token_2)
    # session.bulk_save_objects([u_token_0, u_token_1, u_token_2])
    session.commit()

    # Generate agents
    agent_0 = Agent(ip='192.168.10.12')
    agent_1 = Agent(ip='192.168.10.13')
    agent_2 = Agent(ip='192.168.10.14')
    # session.bulk_save_objects([agent_0, agent_1, agent_2])
    # session.commit()

    # Generate agent tokens
    a_token_0 = AgentAuthToken(agent=agent_0)
    a_token_1 = AgentAuthToken(agent=agent_1)
    a_token_2 = AgentAuthToken(agent=agent_2)
    session.add(a_token_0)
    session.add(a_token_1)
    session.add(a_token_2)
    session.commit()

    # user = session.query(User).filter(User.email == 'person@pie.com').first()
    # authenticates = user.authenticates('password')
    # print('user: %s' % user)
    # print('authenticates: %s' % authenticates)

    # user_token = UserAuthToken(user=user)
    # session.add(user_token)
    # session.commit()
    # print('user_token: %s' % user_token)
    # print('user.token: %s' % user.token)

    # c1 = Cookie(cookie_name='dark chocolate chip',
    #             cookie_recipe_url='http://some.aweso.me/cookie/dark_cc.html',
    #             cookie_sku='CC02',
    #             quantity=1,
    #             unit_cost=0.75)
    # c2 = Cookie(cookie_name='peanut butter',
    #             cookie_recipe_url='http://some.aweso.me/cookie/peanut.html',
    #             cookie_sku='PB01',
    #             quantity=24,
    #             unit_cost=0.25)
    # c3 = Cookie(cookie_name='oatmeal raisin',
    #             cookie_recipe_url='http://some.okay.me/cookie/raisin.html',
    #             cookie_sku='EWW01',
    #             quantity=100,
    #             unit_cost=1.00)
    # session.bulk_save_objects([c1, c2, c3])
    # session.commit()

    # session.add(cookiemon)
    # session.add(cakeeater)
    # session.add(pieperson)

    # o1 = Order()
    # o1.user = cookiemon
    # session.add(o1)

    # line1 = LineItem(cookie=c1, quantity=2, extended_cost=1.00)

    # line2 = LineItem(cookie=c3, quantity=12, extended_cost=3.00)

    # o1.line_items.append(line1)
    # o1.line_items.append(line2)
    # session.commit()

    # o2 = Order()
    # o2.user = cakeeater

    # line1 = LineItem(cookie=c1, quantity=24, extended_cost=12.00)
    # line2 = LineItem(cookie=c3, quantity=6, extended_cost=6.00)

    # o2.line_items.append(line1)
    # o2.line_items.append(line2)

    # session.add(o2)
    # session.commit()
