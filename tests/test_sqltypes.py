import datetime

try:
    from psycopg2ct.compat import register
except ImportError:
    pass
else:
    register()
from pytest import mark, raises, yield_fixture

from sqlalchemy.exc import StatementError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Column

from sqlalchemy_utc import UtcDateTime, utc


Base = declarative_base()
Session = sessionmaker()


@yield_fixture
def fx_connection(fx_engine):
    connection = fx_engine.connect()
    try:
        transaction = connection.begin()
        try:
            metadata = Base.metadata
            metadata.create_all(bind=connection)
            yield connection
        finally:
            transaction.rollback()
    finally:
        connection.close()


@yield_fixture
def fx_session(fx_connection):
    session = Session(bind=fx_connection)
    try:
        yield session
    finally:
        session.close()


class UtcDateTimeTable(Base):

    time = Column(UtcDateTime, primary_key=True)

    __tablename__ = 'tb_utc_datetime'


class FixedOffset(datetime.tzinfo):

    zero = datetime.timedelta(0)

    def __init__(self, offset, name):
        self.offset = offset
        self.name = name

    def utcoffset(self, _):
        return self.offset

    def tzname(self, _):
        return self.name

    def dst(self, _):
        return self.zero


@mark.parametrize('tzinfo', [
    utc,
    FixedOffset(datetime.timedelta(hours=9), 'KST'),
])
def test_utc_datetime(fx_session, tzinfo):
    aware_time = datetime.datetime.now(tzinfo).replace(microsecond=0)
    e = UtcDateTimeTable(time=aware_time)
    fx_session.add(e)
    fx_session.flush()
    saved_time, = fx_session.query(UtcDateTimeTable.time).one()
    assert saved_time == aware_time
    if fx_session.bind.dialect.name in ('sqlite', 'mysql'):
        zero = datetime.timedelta(0)
        assert saved_time.tzinfo.utcoffset(aware_time) == zero
        assert saved_time.tzinfo.dst(aware_time) in (None, zero)


def test_utc_datetime_naive(fx_session):
    with raises((ValueError, StatementError)):
        a = UtcDateTimeTable(time=datetime.datetime.now())
        fx_session.add(a)
        fx_session.flush()


def test_utc_datetime_type(fx_session):
    with raises((TypeError, StatementError)):
        a = UtcDateTimeTable(time=str(datetime.datetime.now()))
        fx_session.add(a)
        fx_session.flush()
