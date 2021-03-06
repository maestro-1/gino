import os
import enum
import random
import string
from datetime import datetime

import aiomysql
import asyncpg
import pytest

from gino import Gino
from gino.dialects.aiomysql import JSON

DB_ARGS = dict(
    host=os.getenv("MYSQL_DB_HOST", "localhost"),
    port=os.getenv("MYSQL_DB_PORT", 3306),
    user=os.getenv("MYSQL_DB_USER", "root"),
    password=os.getenv("MYSQL_DB_PASS", ""),
    db=os.getenv("MYSQL_DB_NAME", "mysql"),
)
MYSQL_URL = "mysql://{user}:{password}@{host}:{port}/{db}".format(**DB_ARGS)
db = Gino()


@pytest.fixture
def random_name(length=8) -> str:
    return _random_name(length)


def _random_name(length=8):
    return "".join(random.choice(string.ascii_letters) for _ in range(length))


class UserType(enum.Enum):
    USER = "USER"


class User(db.Model):
    __tablename__ = "gino_users"

    id = db.Column(db.BigInteger(), primary_key=True)
    nickname = db.Column("name", db.Unicode(255), default=_random_name)
    profile = db.Column("props", JSON(), nullable=False, default="{}")
    type = db.Column(db.Enum(UserType), nullable=False, default=UserType.USER)
    realname = db.StringProperty()
    age = db.IntegerProperty(default=18)
    balance = db.IntegerProperty(default=0)
    birthday = db.DateTimeProperty(default=lambda i: datetime.utcfromtimestamp(0))
    team_id = db.Column(db.ForeignKey("gino_teams.id"))

    @balance.after_get
    def balance(self, val):
        if val is None:
            return 0.0
        return float(val)

    def __repr__(self):
        return "{}<{}>".format(self.nickname, self.id)


class Friendship(db.Model):
    __tablename__ = "gino_friendship"

    my_id = db.Column(db.BigInteger(), primary_key=True)
    friend_id = db.Column(db.BigInteger(), primary_key=True)

    def __repr__(self):
        return "Friends<{}, {}>".format(self.my_id, self.friend_id)


class Relation(db.Model):
    __tablename__ = "gino_relation"

    name = db.Column(db.VARCHAR(255), primary_key=True)


class Team(db.Model):
    __tablename__ = "gino_teams"

    id = db.Column(db.BigInteger(), primary_key=True)
    name = db.Column(db.Unicode(255), default=_random_name)
    parent_id = db.Column(db.ForeignKey("gino_teams.id", ondelete='CASCADE'))
    company_id = db.Column(db.ForeignKey("gino_companies.id"))

    def __init__(self, **kw):
        super().__init__(**kw)
        self._members = set()

    @property
    def members(self):
        return self._members

    @members.setter
    def add_member(self, user):
        self._members.add(user)


class TeamWithDefaultCompany(Team):
    company = Team(name="DEFAULT")


class TeamWithoutMembersSetter(Team):
    def add_member(self, user):
        self._members.add(user)


class Company(db.Model):
    __tablename__ = "gino_companies"

    id = db.Column(db.BigInteger(), primary_key=True)
    name = db.Column(db.Unicode(255), default=_random_name)
    logo = db.Column(db.LargeBinary())

    def __init__(self, **kw):
        super().__init__(**kw)
        self._teams = set()

    @property
    def teams(self):
        return self._teams

    @teams.setter
    def add_team(self, team):
        self._teams.add(team)


class CompanyWithoutTeamsSetter(Company):
    def add_team(self, team):
        self._teams.add(team)


class UserSetting(db.Model):
    __tablename__ = "gino_user_settings"

    # No constraints defined on columns
    id = db.Column(db.BigInteger())
    user_id = db.Column(db.BigInteger())
    setting = db.Column(db.VARCHAR(255))
    value = db.Column(db.Text())
    col1 = db.Column(db.Integer, default=1)
    col2 = db.Column(db.Integer, default=2)

    # Define indexes and constraints inline
    id_pkey = db.PrimaryKeyConstraint("id")
    user_id_fk = db.ForeignKeyConstraint(["user_id"], ["gino_users.id"])
    user_id_setting_unique = db.UniqueConstraint("user_id", "setting")
    col1_check = db.CheckConstraint("col1 >= 1 AND col1 <= 5")
    col2_idx = db.Index("col2_idx", "col2")


def qsize(engine):
    if isinstance(engine.raw_pool, aiomysql.pool.Pool):
        return engine.raw_pool.freesize
    if isinstance(engine.raw_pool, asyncpg.pool.Pool):
        # noinspection PyProtectedMember
        return engine.raw_pool._queue.qsize()
    raise Exception('Unknown pool')
