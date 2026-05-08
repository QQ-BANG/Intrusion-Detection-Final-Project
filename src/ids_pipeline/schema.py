# SQLAlchemy mirror of sql/schema.sql. I keep both because the .sql file is easier for inserts from Python. Same schema either way.
# this too k a lot of time and cross checking because of the sheer amount of components


from sqlalchemy import (
    Column, Integer, Float, String, ForeignKey, Index, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Protocol(Base):
    tableName = "protocols"
    protocol_id = Column(Integer, primary_key=True, autoincrement=True)
    protocol_name = Column(String, nullable=False, unique=True)


class Service(Base):
    tableName = "services"
    service_id = Column(Integer, primary_key=True, autoincrement=True)
    service_name = Column(String, nullable=False, unique=True)


class Flag(Base):
    tableName = "flags"
    flag_id = Column(Integer, primary_key=True, autoincrement=True)
    flag_name = Column(String, nullable=False, unique=True)


class AttackType(Base):
    tableName = "attack_types"
    attack_id = Column(Integer, primary_key=True, autoincrement=True)
    attack_label = Column(String, nullable=False, unique=True)
    attack_family = Column(String, nullable=False)
    is_attack = Column(Integer, nullable=False)


class Connection(Base):
    tableName = "connections"
    conn_id = Column(Integer, primary_key=True, autoincrement=True)
    split = Column(String, nullable=False)

    duration = Column(Integer, nullable=False)
    protocol_id = Column(Integer, ForeignKey("protocols.protocol_id"), nullable=False)
    service_id = Column(Integer, ForeignKey("services.service_id"), nullable=False)
    flag_id = Column(Integer, ForeignKey("flags.flag_id"), nullable=False)
    src_bytes = Column(Integer, nullable=False)
    dst_bytes = Column(Integer, nullable=False)
    land = Column(Integer, nullable=False)
    wrong_fragment = Column(Integer, nullable=False)
    urgent = Column(Integer, nullable=False)
    hot = Column(Integer, nullable=False)
    num_failed_logins = Column(Integer, nullable=False)
    logged_in = Column(Integer, nullable=False)
    num_compromised = Column(Integer, nullable=False)
    root_shell = Column(Integer, nullable=False)
    su_attempted = Column(Integer, nullable=False)
    num_root = Column(Integer, nullable=False)
    num_file_creations = Column(Integer, nullable=False)
    num_shells = Column(Integer, nullable=False)
    num_access_files = Column(Integer, nullable=False)
    num_outbound_cmds = Column(Integer, nullable=False)
    is_host_login = Column(Integer, nullable=False)
    is_guest_login = Column(Integer, nullable=False)
    count = Column(Integer, nullable=False)
    srv_count = Column(Integer, nullable=False)
    serror_rate = Column(Float, nullable=False)
    srv_serror_rate = Column(Float, nullable=False)
    rerror_rate = Column(Float, nullable=False)
    srv_rerror_rate = Column(Float, nullable=False)
    same_srv_rate = Column(Float, nullable=False)
    diff_srv_rate = Column(Float, nullable=False)
    srv_diff_host_rate = Column(Float, nullable=False)
    dst_host_count = Column(Integer, nullable=False)
    dst_host_srv_count = Column(Integer, nullable=False)
    dst_host_same_srv_rate = Column(Float, nullable=False)
    dst_host_diff_srv_rate = Column(Float, nullable=False)
    dst_host_same_src_port_rate = Column(Float, nullable=False)
    dst_host_srv_diff_host_rate = Column(Float, nullable=False)
    dst_host_serror_rate = Column(Float, nullable=False)
    dst_host_srv_serror_rate = Column(Float, nullable=False)
    dst_host_rerror_rate = Column(Float, nullable=False)
    dst_host_srv_rerror_rate = Column(Float, nullable=False)
    attack_id = Column(Integer, ForeignKey("attack_types.attack_id"), nullable=False)
    difficulty = Column(Integer, nullable=True)

    protocol = relationship("Protocol")
    service = relationship("Service")
    flag = relationship("Flag")
    attack = relationship("AttackType")


Index("idx_conn_split", Connection.split)
Index("idx_conn_protocol", Connection.protocol_id)
Index("idx_conn_service", Connection.service_id)
Index("idx_conn_flag", Connection.flag_id)
Index("idx_conn_attack", Connection.attack_id)


def get_engine(db_url):
    engine = create_engine(db_url, future=True)
    # sqlite doesn't enforce foreign keys unless I tell it to. without this PRAGMA we wouldn't catch dangling FKs at insert time
    if db_url.startswith("sqlite"):
        from sqlalchemy import event

        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _rec):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.close()

    return engine


def get_session(engine):
    return sessionmaker(bind=engine, autoflush=False, future=True)()
