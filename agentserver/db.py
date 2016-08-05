from datetime import datetime, timedelta

from sqlalchemy import (Column, Integer, Numeric, String, DateTime, ForeignKey,
                        Boolean, create_engine)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, sessionmaker, validates
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.event import listen
from sqlalchemy import desc

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
        return "<ProcessDetail(id='{self.id}', " \
            "name='{self.name}', " \
            "agent='{self.agent.name}', " \
            "start='{self.start}', " \
            "created_on='{self.created_on}')>".format(self=self)

    @classmethod
    def update_or_create(self, name, agent_id, start, session=None):
        if session is None:
            session = dal.session
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

    @classmethod
    def started_from(self, agent_id, start, session=None):
        if session is None:
            session = dal.session
        details = session.query(ProcessDetail) \
        .filter(ProcessDetail.agent_id == agent_id,
                ProcessDetail.start >= start)
        return details


class ProcessState(Base):
    __tablename__ = 'processstates'

    id = Column(Integer(), primary_key=True)
    detail_id = Column(Integer(), ForeignKey('processdetails.id'))
    name = Column(String(), nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    detail = relationship("ProcessDetail", backref=backref('processstates', order_by=desc(created_on)))

    def __repr__(self):
        return "<ProcessState(id='{self.id}', " \
            "name='{self.name}', " \
            "detail='{self.detail.name}', " \
            "created_on='{self.created_on}')>".format(self=self)

    # @classmethod
    # def latest(self, detail, session=None):
    #     if session is None:
    #         session = dal.session
    #     try:
    #         return session.query(ProcessState) \
    #         .filter(ProcessState.detail_id == detail.id) \
    #         .order_by(desc(ProcessState.created_on)).one()
    #     except NoResultFound:
    #         return None


class Agent(Base):
    __tablename__ = 'agents'

    id = Column(Integer(), primary_key=True)
    name = Column(String(), nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    def __repr__(self):
        return "<Agent(ip='{self.ip}', " \
            "name='{self.name}', " \
            "created_on='{self.created_on}')>".format(self=self)

    def process_states(self, delta=timedelta(weeks=6), session=None):
        if session is None:
            session = dal.session
        details = session.query(ProcessDetail) \
                    .filter(ProcessDetail.agent_id == self.id) \
                    .all()
        return details
        # states = []
        # join = session.query()


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
