from datetime import datetime, timedelta

from sqlalchemy import (Column, Integer, Numeric, String, DateTime, ForeignKey,
                        Boolean, create_engine, desc, Enum)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, validates
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.event import listen
import os, subprocess, json

from pydruid.client import PyDruid
from pydruid.utils.aggregators import doublesum
from pydruid.utils.filters import Dimension, Filter

from kafka import KafkaProducer

from passlib.apps import custom_app_context as pwd_context

from utils import (uuid, validate_iso_8601_period,
    validate_iso_8601_interval, iso_8601_interval_to_datetimes,
    iso_8601_period_to_timedelta)

import random


Base = declarative_base()


class Agent(Base):
    __tablename__ = 'agents'

    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    @classmethod
    def authorize(cls, authorization_token, session=None):
        if not session:
            session = dal.Session()
        return session.query(AgentAuthToken) \
            .filter(AgentAuthToken.uuid == authorization_token) \
            .one().agent

    def __repr__(self):
        return "<Agent(id='{self.id}', " \
            "name='{self.name}', " \
            "created_on='{self.created_on}')>".format(self=self)


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

    @classmethod
    def detail_for_agent_id(cls, id):
        return dal.Session().query(AgentDetail) \
            .filter(AgentDetail.agent_id == id).one()

    @classmethod
    def update_or_create(cls, id, dist_name, dist_version,
        hostname, num_cores, memory, processor, session=None):
        if not session:
            session = dal.session
        try:
            detail = session.query(AgentDetail) \
                .filter(AgentDetail.agent_id == id).one()
            detail.hostname=hostname
            detail.processor=processor
            detail.num_cores=num_cores
            detail.memory=memory
            detail.dist_name=dist_name
            detail.dist_version=dist_version
            session.commit()
            return False
        except NoResultFound:
            session.add(AgentDetail(agent_id = id,
                hostname=hostname, processor=processor,
                num_cores=num_cores, memory=memory,
                dist_name=dist_name, dist_version=dist_version))
            session.commit()
            return True

    def __repr__(self):
        return "<AgentDetail(id='{self.id}', " \
            "agent_id='{self.agent_id}', " \
            "hostname='{self.hostname}', " \
            "processor='{self.processor}', " \
            "num_cores='{self.num_cores}', " \
            "memory='{self.memory}', " \
            "dist_name='{self.dist_name}', " \
            "dist_version='{self.dist_version}', " \
            "updated_on='{self.updated_on}, '" \
            "created_on='{self.created_on}')>".format(self=self)

    def __json__(self):
        return {'hostname': self.hostname,
            'processor': self.processor,
            'num_cores': self.num_cores,
            'memory': self.memory,
            'dist_name': self.dist_name,
            'dist_version': self.dist_version,
            'updated': self.updated_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            'created': self.created_on.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}


class AgentAuthToken(Base):
    __tablename__ = 'agentauthtokens'

    uuid = Column(String(), primary_key=True, default=uuid)
    agent_id = Column(Integer(), ForeignKey('agents.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    agent = relationship("Agent", backref=backref('token',
        cascade='all,delete,delete-orphan', uselist=False))

    def __repr__(self):
        return "<AgentAuthToken(uuid='{self.uuid}', " \
            "agent_id='{self.agent_id}', " \
            "created_on='{self.created_on}')>".format(self=self)


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
        return "<User(name='{self.name}', " \
            "email='{self.email}', " \
            "is_admin='{self.is_admin}', " \
            "password='{self.password}')>".format(self=self)

def hash_password(target, value, oldvalue, initiator):
    "hashes password"
    return pwd_context.encrypt(value)

listen(User.password, 'set', hash_password, retval=True)


class UserAuthToken(Base):
    __tablename__ = 'userauthtokens'

    uuid = Column(String(), primary_key=True, default=uuid)
    user_id = Column(Integer(), ForeignKey('users.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    user = relationship("User",
        backref=backref('token', cascade='all,delete,delete-orphan', uselist=False),
        single_parent=True)

    def __repr__(self):
        return "<UserAuthToken(uuid='{self.uuid}', " \
            "user_id='{self.user_id}', " \
            "created_on='{self.created_on}')>".format(self=self)  


class DataAccessLayer:
    def __init__(self):
        # http://pythoncentral.io/understanding-python-sqlalchemy-session/
        self.engine = None
        self.Session = None
        self.conn_string = None
        self.session = None

    def connect(self, conn_string=None):
        self.conn_string = conn_string
        if self.conn_string:
            self.engine = create_engine(self.conn_string)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            self.session = self.Session()

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

    def write_stats(self, id, name, stats, **kwargs):
        for stat in stats:
            msg = {'agent_id': id, 'process_name': name,
                'timestamp': datetime.utcfromtimestamp(stat[0]).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                'cpu': stat[1], 'mem': stat[2]}
            self.connection.send('supervisor', msg)
        self.connection.flush()

kal = KafkaAccessLayer()


class PyDruidResultMock(object):
    def __init__(self, result):
        self.result = result


class PyDruidMock(object):
    def groupby(self, datasource, granularity, intervals, dimensions,
        filter, aggregations):
        f = Filter.build_filter(filter)
        if f['type'] == 'selector' and f['dimension'] == 'agent_id' and 'value' in f:
            try:
                body = open(os.path.join(self.fixtures_dir,
                    'groupby{0}.json'.format(f['value']))).read().decode('utf-8')
            except:
                body = '[]'
        else:
            body = '[]'
        return PyDruidResultMock(body)

    def __granularity_to_timedelta__(self, granularity):
        if granularity == 'none' or granularity == 'second':
            return timedelta(seconds=1)
        elif granularity == 'minute':
            return timedelta(minutes=1)
        elif granularity == 'fifteen_minute':
            return timedelta(minutes=15)
        elif granularity == 'thirty_minute':
            return timedelta(minutes=30)
        elif granularity == 'hour':
            return timedelta(hours=1)
        elif granularity == 'day':
            return timedelta(days=1)
        elif granularity == 'week':
            return timedelta(weeks=1)
        elif granularity == 'month':
            return timedelta(days=30)
        elif granularity == 'quarter':
            return timedelta(days=30 * 4)
        elif granularity == 'year':
            return timedelta(days=365)
        else:
            return timedelta(hours=1)

    def timeseries(self, datasource, granularity, descending, intervals,
        aggregations, context, filter):
        f = Filter.build_filter(filter)
        if f['type'] == 'and' and f['fields'][0]['type'] == 'selector' and \
            f['fields'][0]['dimension'] == 'agent_id' and \
            f['fields'][1]['type'] == 'selector' and \
            f['fields'][1]['dimension'] == 'process_name':
            agent_id = f['fields'][0]['value']
            process_name = f['fields'][1]['value']

            (interval_start, interval_end) = iso_8601_interval_to_datetimes(intervals)
            if interval_end is None:
                interval_end = datetime.now()

            if granularity in DruidAccessLayer.timeseries_granularities:
                query_granularity = self.__granularity_to_timedelta__(granularity)
            else:
                query_granularity = iso_8601_period_to_timedelta(granularity['period'])

            body = []
            curr_time = interval_start

            while curr_time < interval_end:
                body.append({'timestamp': curr_time.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                    'result': {'cpu': random.uniform(0, 1),
                    'mem': random.randint(1, 10000000)}})
                curr_time += query_granularity
        else:
            body = []
        return PyDruidResultMock(body)

    def select(self, datasource, granularity, intervals, descending,
        dimensions, metrics, filter, paging_spec):
        f = Filter.build_filter(filter)
        print('f: %s' % f)
        body = []
        return PyDruidResultMock(body)


class DruidAccessLayer(object):
    timeseries_granularities = ['none', 'second', 'minute',
        'fifteen_minute', 'thirty_minute','hour', 'day',
        'week', 'month', 'quarter', 'year']

    select_granularities = ['all', 'second', 'minute',
        'fifteen_minute', 'thirty_minute','hour', 'day',
        'week', 'month', 'quarter', 'year']

    def __init__(self):
        self.connection = None

    def connect(self, uri):
        if uri.lower() == 'debug':
            self.connection = PyDruidMock()
        else:
            self.connection = PyDruid('http://{0}'.format(uri), 'druid/v2/')

    def __longmax__(self, raw_metric):
        return {"type": "longMax", "fieldName": raw_metric} 

    def __doublemax__(self, raw_metric):
        return {"type": "doubleMax", "fieldName": raw_metric}

    def __validate_granularity__(self, granularity, supported_granularities):
        if granularity in self.timeseries_granularities:
            query_granularity = granularity
        elif validate_iso_8601_period(granularity):
            query_granularity = {'type': 'period', 'period': granularity}
        else:
            raise ValueError('Unsupported granularity "{0}"'.format(granularity))
        return query_granularity

    def __validate_intervals__(self, intervals):
        if not validate_iso_8601_interval(intervals):
            raise ValueError('Unsupported interval "{0}"'.format(intervals))
        return intervals

    def timeseries(self, agent_id, process_name, granularity='none',
            intervals='P6W', descending=False):
        query_granularity = self.__validate_granularity__(granularity,
            self.timeseries_granularities)
        intervals = self.__validate_intervals__(intervals)

        return self.connection.timeseries(
            datasource='supervisor',
            granularity=query_granularity,
            descending= descending,
            intervals=intervals,
            aggregations={'cpu': self.__doublemax__('cpu'),
                'mem': self.__longmax__('mem')},
            context={'skipEmptyBuckets': 'true'},
            filter=(Dimension('agent_id') == agent_id) &
                (Dimension('process_name') == process_name))

    def select(self, agent_id, process_name, granularity='all',
            intervals='P6W', descending=True):
        query_granularity = self.__validate_granularity__(granularity,
            self.select_granularities)
        intervals = self.__validate_intervals__(intervals)

        return self.connection.select(
            datasource='supervisor',
            granularity=query_granularity,
            intervals=intervals,
            descending= descending,
            dimensions=['process_name'],
            metrics=['cpu', 'mem'],
            filter=(Dimension('agent_id') == agent_id) &
                (Dimension('process_name') == process_name),
            paging_spec={'pagingIdentifiers': {}, "threshold":1}
        )

dral = DruidAccessLayer()


class PlyQLAccessLayer(object):
    def __init__(self):
        self.uri = None

    def connect(self, uri):
        if uri.lower() == 'debug':
            self.uri = 'debug'
        else:
            self.uri = uri

    def query(self, q, interval=None):
        if not self.uri:
            raise UnboundLocalError('Please connect to valid uri before calling query.')

        command = ['plyql', '-h', self.uri, '-q', q, '-o', 'json']
        if interval:
            command.extend(['-i', interval])
        process = subprocess.Popen(command, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE)
        out, err = process.communicate()
        if err:
            return json.dumps({'error': err.strip()})
        else:
            return out

    def processes(self, agent_id, period='P6W'):
        return self.query('SELECT process_name AS process, ' \
            'COUNT() AS count, MAX(__time) AS time FROM supervisor ' \
            'WHERE agent_id = "{0}" GROUP BY process_name;'
            .format(agent_id), period)

pal = PlyQLAccessLayer()
