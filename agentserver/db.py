from datetime import datetime

from sqlalchemy import (Column, Integer, Numeric, String, DateTime, ForeignKey,
                        Boolean, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, validates
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.event import listen

from kafka import KafkaProducer

from passlib.apps import custom_app_context as pwd_context

from utils import uuid


Base = declarative_base()


STATE_MAP = {
    'STOPPED': 0,
    'STARTING': 10,
    'RUNNING': 20,
    'BACKOFF': 30,
    'STOPPING': 40,
    'EXITED': 100,
    'FATAL': 200,
    'UNKNOWN': 1000 
}


class ProcessDetail(Base):
    __tablename__ = 'processdetails'

    id = Column(Integer(), primary_key=True)
    agent_id = Column(Integer(), ForeignKey('agents.id'))
    name = Column(String(), nullable=False)
    start = Column(DateTime())

    created_on = Column(DateTime(), default=datetime.now)

    agent = relationship("Agent", backref=backref('processdetails'))

    def __repr__(self):
        return "ProcessDetail(id='{self.id}', " \
            "name='{self.name}', " \
            "agent='{self.agent.name}', " \
            "start='{self.start}', " \
            "created_on='{self.created_on}')".format(self=self)

    @classmethod
    def update_or_create(self, name, agent_id, start, session=None):
        if session is None:
            session = dal.Session()
        try:
            detail = session.query(ProcessDetail) \
            .filter(ProcessDetail.agent_id == agent_id,
                    ProcessDetail.name == name).one()
            if detail.start != start:
                detail.start = start
                session.commit()
        except NoResultFound:
            detail = ProcessDetail(name=name,
                agent_id=agent_id, start=start)
            session.add(detail)
            session.commit()
        return detail


class ProcessState(Base):
    __tablename__ = 'processstates'

    id = Column(Integer(), primary_key=True)
    detail_id = Column(Integer(), ForeignKey('processdetails.id'))
    name = Column(String(), nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    detail = relationship("ProcessDetail", backref=backref('processdetails'))

    def __repr__(self):
        return "ProcessState(id='{self.id}', " \
            "name='{self.name}', " \
            "detail='{self.detail.name}', " \
            "created_on='{self.created_on}')".format(self=self)


class Agent(Base):
    __tablename__ = 'agents'

    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    def __repr__(self):
        return "Agent(ip='{self.ip}', " \
            "name='{self.name}', " \
            "created_on='{self.created_on}')".format(self=self)


class AgentDetail(Base):
    __tablename__ = 'agentdetails'

    id = Column(Integer(), primary_key=True)
    agent_id = Column(Integer(), ForeignKey('agents.id'), unique=True)
    hostname = Column(String, nullable=False)
    processor = Column(String(), nullable=False)
    num_cores = Column(Integer(), default=1)
    memory = Column(Integer(), default=0)
    dist_name = Column(String(), nullable=False)
    dist_version = Column(String(), nullable=False)
    updated_on = Column(DateTime(), default=datetime.now, onupdate=datetime.now)
    created_on = Column(DateTime(), default=datetime.now)

    agent = relationship("Agent", backref=backref('details', uselist=False))

    def __repr__(self):
        return "AgentDetail(id='{self.id}', " \
            "agent_id='{self.agent_id}', " \
            "hostname='{self.hostname}', " \
            "processor='{self.processor}', " \
            "num_cores='{self.num_cores}', " \
            "memory='{self.memory}', " \
            "dist_name='{self.dist_name}', " \
            "dist_version='{self.dist_version}', " \
            "updated_on='{self.updated_on}, '" \
            "created_on='{self.created_on}')".format(self=self)


class AgentAuthToken(Base):
    __tablename__ = 'agentauthtokens'

    uuid = Column(String(), primary_key=True, default=uuid)
    agent_id = Column(Integer(), ForeignKey('agents.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    agent = relationship("Agent", backref=backref('token', uselist=False))

    def __repr__(self):
        return "AgentAuthToken(uuid='{self.uuid}', " \
            "agent_id='{self.agent_id}', " \
            "created_on='{self.created_on}')".format(self=self)


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
            "created_on='{self.created_on}')".format(self=self)  


class DataAccessLayer:
    def __init__(self):
        # http://pythoncentral.io/understanding-python-sqlalchemy-session/
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


class KafkaProducerMock(object):
    def __init__(self, bootstrap_servers=None, value_serializer=None):
        pass
    def send(self, topic, data):
        pass
    def flush(self):
        pass


class KafkaAccessLayer(object): 
    def __init__(self):
        self.connection = None

    def connect(self, uri):
        if uri.lower() == 'debug':
            self.connection = KafkaProducerMock()
        else:
            self.connection = KafkaProducer(bootstrap_servers=uri,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'))


kal = KafkaAccessLayer()

# import re
# class AgentEvent(Base):
#     __tablename__ = 'agent_events'
#     id = Column(Integer(), primary_key=True)
#     ip = Column(String(), nullable=False)
#     agent_id = Column(Integer(), ForeignKey('agents.id'))
#     created_on = Column(DateTime(), default=datetime.now)
#     event = Column(String(), nullable=False)

#     agent = relationship("Agent", backref=backref('events', uselist=True))

#     @validates('ip')
#     def validate_ip(self, key, ipadddress):
#         """
#         Validates an IPv4 or IPv6 IP address
#         """
#         regex = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$|' \
#             '(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}| ' \
#                 '([0-9a-fA-F]{1,4}:){1,7}:|' \
#                 '([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|' \
#                 '([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|' \
#                 '([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|' \
#                 '([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|' \
#                 '([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|' \
#                 '[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|' \
#                 ':((:[0-9a-fA-F]{1,4}){1,7}|:)|' \
#                 'fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|' \
#                 '::(ffff(:0{1,4}){0,1}:){0,1}' \
#                 '((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}' \
#                 '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|' \
#                 '([0-9a-fA-F]{1,4}:){1,4}:' \
#                 '((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}' \
#                 '(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])' \
#                 ')')
#         result = regex.match(ipadddress)
#         assert result != None
#         return ipadddress

#     @validates('event')
#     def validate_event(self, key, event):
#         """
#         Validates an agent event.
#         """
#         assert (event == 'C' or event == 'D')
#         return event

#     def __repr__(self):
#         return "AgentEvent(ip='{self.ip}', " \
#             "name='{self.agent.name}', " \
#             "event='{self.event}', " \
#             "created_on='{self.created_on}'".format(self=self)

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

# from itertools import takewhile, islice, tee

# class SupervisorSeries(object):
#     series_name = 'supervisor'
#     # Defines all the fields in this time series.
#     fields = ['cpu', 'mem', 'time']
#     # Defines all the tags for the series.
#     tags = ['processgroup', 'processname']

#     @classmethod
#     def Aggregate(cls, resultset, processes, starttime, timedelta, func):
#         """
#         Aggregates resultset using processes, timedelta, and func.
#         resultset: generator for influxdb query
#         processes: list of (processgroup, processname) tuples for filtering
#         starttime: the start time over which to accumulate results
#         timedelta: the time period over which to apply func
#         func: function that reduces results: Max, Min, Sum
#         returns: a list of dictionaries with keys 'processgroup', 'processname', and 'supervisorseries'
#         """
#         def aggregate_helper(iterator, currenttime, timedelta, func, acc):
#             it_0, it_1 = tee(iterator)
#             try:
#                 it_0.next()

#                 def less_than_time(item):
#                     return item.time < (currenttime + timedelta)

#                 subset = list(takewhile(less_than_time, it_1))
#                 islice(it_0, 0, len(subset) - 1) # Already popped off one result in it_0.next() call above.
#                 mapreduce = reduce(func, map(SupervisorSeries, arr))
#                 if func == SupervisorSeries.Sum:
#                     mapreduce = SupervisorSeries.Div(mapreduce, len(subset))
#                 acc.append(mapreduce)
#             except StopIteration as e:
#                 print('StopIteration: {0}'.format(str(e)))
#                 return acc

#         results = []
#         for process in processes:
#             filtered_resultset = resultset.get_points(tags={'groupname': process[0], 'processname': process[1]})
#             aggregate = aggregate_helper(filtered_resultset, starttime, timedelta, func, [])
#             results.append({ 'processgroup': process[0], 'processname': process[1], 'series': aggregate })
#         return results


#         # def helper(iterator, timedelta, func, currenttime, acc):
#         #     it_0, it_1 = tee(iterator)
#         #     try:
#         #         it_1.next()
#         #         def less_than_time(item):
#         #             return item.time < (currenttime + timedelta)

#         #         # Expect a relatively small subset to be returned.
#         #         subset = list(takewhile(less_than_time, it_0))
#         #         islice(it_1, 0, len(subset) - 1) # Because we've already popped off one result in it_1.next() call above.
#         #         result = reduce(func, subset)
#         #         acc.append(result)

#         #         return helper(it_1, timedelta, func, currentime + timedelta, acc)
#         #     except StopIteration as e:
#         #         print('e: %s' % e)
#         #         return acc

#     @classmethod
#     def Max(cls, s1, s2):
#         data = {'cpu': max(s1.cpu, s2.cpu), 'mem': max(s1.mem, s2.mem),
#         'time': max(s1.time, s2.time), 'processgroup': s1.processgroup,
#         'processname': s1.processname}
#         return SupervisorSeries(data)

#     @classmethod
#     def Min(cls, s1, s2):
#         data = {'cpu': min(s1.cpu, s2.cpu), 'mem': min(s1.mem, s2.mem),
#         'time': min(s1.time, s2.time), 'processgroup': s1.processgroup,
#         'processname': s1.processname}
#         return SupervisorSeries(data)

#     @classmethod
#     def Sum(cls, s1, s2):
#         data = {'cpu': s1.cpu + s2.cpu, 'mem': s1.mem + s2.mem,
#         'time': s1.time + s2.time, 'processgroup': s1.processgroup,
#         'processname': s1.processname}
#         return SupervisorSeries(data)

#     @classmethod
#     def Div(cls, s1, div=1.0):
#         data = {'cpu': s1.cpu / float(div), 'mem': s1.mem / float(div),
#         'time': s1.time / float(div), 'processgroup': s1.processgroup,
#         'processname': s1.processname }
#         return SupervisorSeries(data)

#     def __init__(self, data):
#         self.cpu = data['cpu']
#         self.mem = data['mem']
#         self.time = data['time']

#         self.processgroup = data['processgroup']
#         self.processname = data['processname']
