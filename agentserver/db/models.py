from datetime import datetime
from sqlalchemy import (Column, Integer, String, DateTime, ForeignKey,
                        Boolean, create_engine)
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import relationship, backref, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.event import listen
from sqlalchemy.exc import ArgumentError, NoSuchModuleError, OperationalError
from passlib.apps import custom_app_context as pwd_context
from agentserver.utils.uuid import uuid


# Mixins
class AllMixin(object):

    @classmethod
    def all(cls, session=None):
        if not session:
            session = models.session
        return session.query(cls).all()


class CountMixin(object):

    @classmethod
    def count(cls, session=None):
        if not session:
            session = models.session
        return session.query(cls).count()


class DeleteMixin(object):

    def delete(self, session=None):
        if not session:
            session = models.session
        try:
            session.delete(self)
            session.commit()
            return True
        except Exception:
            return False


class GetMixin(object):

    @classmethod
    def get(cls, session=None, *args, **kwargs):
        """Find object with keyword args."""
        if not session:
            session = models.session

        query = None
        for k, v in kwargs.items():
            if query is None:
                query = session.query(cls).filter(getattr(cls, k) == v)
            else:
                query = query.filter(getattr(cls, k) == v)
        try:
            return query.one()
        except (AttributeError, NoResultFound):
            return None


class IDMixin(object):
    id = Column(Integer, primary_key=True)


class SaveMixin(object):

    def save(self, session=None):
        if not session:
            session = models.session
        session.add(self)
        session.commit()
        return self


class SaveAllMixin(object):

    @classmethod
    def save_all(cls, items, session=None):
        if not session:
            session = models.session
        session.add_all(items)
        session.commit()


class Base(object):

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()


Base = declarative_base(cls=Base)


class Agent(Base, IDMixin, AllMixin, CountMixin, DeleteMixin,
            GetMixin, SaveMixin, SaveAllMixin):

    name = Column(String(), nullable=False, unique=True)
    created_on = Column(DateTime(), default=datetime.now)

    @property
    def created(self):
        return self.created_on.strftime('%d-%m-%Y %H:%M:%S')

    @classmethod
    def authorize(cls, authorization_token, session=None):
        if not session:
            session = models.session
        try:
            return session.query(AgentAuthToken) \
                .filter(AgentAuthToken.uuid == authorization_token) \
                .one().agent
        except NoResultFound:
            return None

    def __repr__(self):
        return "<Agent(id='{self.id}', " \
            "name='{self.name}', " \
            "created_on='{self.created_on}')>".format(self=self)


class AgentDetail(Base, IDMixin, CountMixin, DeleteMixin, SaveMixin):

    agent_id = Column(Integer(), ForeignKey(
        'agent.id'), unique=True, nullable=False)
    hostname = Column(String, nullable=False)
    processor = Column(String(), nullable=False)
    num_cores = Column(Integer(), default=1)
    memory = Column(Integer(), default=0)
    dist_name = Column(String(), nullable=False)
    dist_version = Column(String(), nullable=False)
    updated_on = Column(DateTime(), default=datetime.now,
                        onupdate=datetime.now)
    created_on = Column(DateTime(), default=datetime.now)

    cascade = 'all,delete,delete-orphan'
    backref = backref('detail', cascade=cascade, uselist=False)
    agent = relationship('Agent', backref=backref)

    @property
    def created(self):
        return self.created_on.strftime('%d-%m-%Y %H:%M:%S')

    @property
    def updated(self):
        return self.updated_on.strftime('%d-%m-%Y %H:%M:%S')

    @classmethod
    def detail_for_agent_id(cls, id):
        try:
            return models.Session().query(AgentDetail) \
                .filter(AgentDetail.agent_id == id).one()
        except NoResultFound:
            return None

    @classmethod
    def update_or_create(cls, id, dist_name, dist_version,
                         hostname, num_cores, memory, processor, session=None):
        if not session:
            session = models.session
        try:
            detail = session.query(AgentDetail) \
                .filter(AgentDetail.agent_id == id).one()
            detail.hostname = hostname
            detail.processor = processor
            detail.num_cores = num_cores
            detail.memory = memory
            detail.dist_name = dist_name
            detail.dist_version = dist_version
            session.commit()
            return False
        except NoResultFound:
            session.add(AgentDetail(agent_id=id,
                                    hostname=hostname, processor=processor,
                                    num_cores=num_cores, memory=memory,
                                    dist_name=dist_name,
                                    dist_version=dist_version))
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
            "updated_on='{self.updated_on}', " \
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


class AgentAuthToken(Base, AllMixin, CountMixin, DeleteMixin,
                     GetMixin, SaveMixin, SaveAllMixin):

    uuid = Column(String(), primary_key=True, default=uuid)
    agent_id = Column(Integer(), ForeignKey(
        'agent.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    cascade = 'all,delete,delete-orphan'
    backref = backref('token', cascade=cascade, uselist=False)
    agent = relationship('Agent', backref=backref)

    @property
    def created(self):
        return self.created_on.strftime('%d-%m-%Y %H:%M:%S')

    def __repr__(self):
        return "<AgentAuthToken(uuid='{self.uuid}', " \
            "agent_id='{self.agent_id}', " \
            "created_on='{self.created_on}')>".format(self=self)


class UserAuthenticationException(Exception):

    def __init__(self, message, username, password):
        self.message = message
        self.username = username
        self.password = password

    def __repr__(self):
        return 'Authentication failed for username: {self.username}, ' \
            'password: {self.password}. Reason: {self.message}.'.format(
                self=self)


class User(Base, IDMixin, AllMixin, CountMixin,
           DeleteMixin, GetMixin, SaveMixin, SaveAllMixin):

    name = Column(String(), nullable=False)
    email = Column(String(), nullable=False, unique=True)
    password = Column(String(), nullable=False)
    is_admin = Column(Boolean(), default=False)
    created_on = Column(DateTime(), default=datetime.now)
    updated_on = Column(DateTime(), default=datetime.now,
                        onupdate=datetime.now)

    @classmethod
    def authorize(cls, authorization_token, session=None):
        if not session:
            session = models.session
        try:
            return session.query(UserAuthToken) \
                .filter(UserAuthToken.uuid == authorization_token) \
                .one().user
        except NoResultFound:
            return None

    @classmethod
    def authenticate(cls, username, password, session=None):
        if session is None:
            session = models.session
        try:
            user = session.query(User).filter(User.email == username).one()
            if user.authenticates(password):
                try:
                    token = session.query(UserAuthToken).filter(
                        UserAuthToken.user == user).one()
                except NoResultFound:
                    token = UserAuthToken(user=user)
                    session.add(token)
                    session.commit()
                return token.uuid
            else:
                raise UserAuthenticationException(
                    'incorrect password for', username, password)
        except NoResultFound:
            raise UserAuthenticationException(
                'unknown username', username, password)

    @property
    def created(self):
        return self.created_on.strftime('%d-%m-%Y %H:%M:%S')

    @property
    def updated(self):
        return self.updated_on.strftime('%d-%m-%Y %H:%M:%S')

    @property
    def admin(self):
        if self.is_admin:
            return 'Y'
        else:
            return 'N'

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
    # "hashes password"
    return pwd_context.encrypt(value)

listen(User.password, 'set', hash_password, retval=True)


class UserAuthToken(Base, AllMixin, CountMixin, DeleteMixin,
                    GetMixin, SaveMixin, SaveAllMixin):

    uuid = Column(String(), primary_key=True, default=uuid)
    user_id = Column(Integer(), ForeignKey(
        'user.id'), unique=True, nullable=False)
    created_on = Column(DateTime(), default=datetime.now)

    cascade = 'all,delete,delete-orphan'
    backref = backref('token', cascade=cascade, uselist=False)
    user = relationship("User", backref=backref, single_parent=True)

    @classmethod
    def authorize(cls, authorization_token, session=None):
        if not session:
            session = models.session
        return session.query(UserAuthToken) \
            .filter(UserAuthToken.uuid == authorization_token) \
            .one().user

    @property
    def created(self):
        return self.created_on.strftime('%d-%m-%Y %H:%M:%S')

    def __repr__(self):
        return "<UserAuthToken(uuid='{self.uuid}', " \
            "user_id='{self.user_id}', " \
            "created_on='{self.created_on}')>".format(self=self)


class ModelAccessLayer:

    def __init__(self):
        # http://pythoncentral.io/understanding-python-sqlalchemy-session/
        self.engine = None
        self.Session = None
        self.conn_string = None
        self.session = None

    def connect(self, conn_string=None):
        self.conn_string = conn_string
        if self.conn_string:
            try:
                self.engine = create_engine(self.conn_string)
                Base.metadata.create_all(self.engine)
                self.Session = sessionmaker(bind=self.engine)
                self.session = self.Session()
            except OperationalError as e:
                message = e.orig.message.split('\n')[0].strip()
                raise Exception(
                    'Database connection error: {0}'.format(message))
            except NoSuchModuleError as e:
                message = e.message.split(':')[-1]
                raise Exception(
                    'Database connection error: unknown database type "{0}"'
                    .format(message))
            except ArgumentError as e:
                raise Exception(
                    'Database connection error: {0}'.format(e.message))
            except Exception as e:
                raise Exception(
                    'Database connection error: {0}'.format(e.message))
        else:
            raise Exception(
                'Database connection error: connection cannot be none.')

models = ModelAccessLayer()
