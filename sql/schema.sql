-- Relational schema
-- Source data: NSL-KDD (cleaned version of the DARPA 1998/1999 corpus).
--   * 3NF for the categorical dimensions.
--   * One fact table `connections`, one row per network connection,
--     with FKs into the dimension tables.
--   * `attack_types` maps the 39 specific labels to the four DARPA
--     families ('dos','probe','r2l','u2r') or 'normal'.
--   * Indexes on FKs and on `split` because most queries group on them.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS protocols (
    protocol_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    protocol_name TEXT    NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS services (
    service_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    service_name TEXT    NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS flags (
    flag_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_name TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS attack_types (
    attack_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    attack_label  TEXT    NOT NULL UNIQUE,   -- e.g. 'neptune', 'normal'
    attack_family TEXT    NOT NULL,          -- 'dos','probe','r2l','u2r','normal'
    is_attack     INTEGER NOT NULL           -- 0 for 'normal', else 1
);

CREATE TABLE IF NOT EXISTS connections (
    conn_id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    split                         TEXT    NOT NULL,   -- 'train' | 'test'
    duration                      INTEGER NOT NULL,
    protocol_id                   INTEGER NOT NULL REFERENCES protocols(protocol_id),
    service_id                    INTEGER NOT NULL REFERENCES services(service_id),
    flag_id                       INTEGER NOT NULL REFERENCES flags(flag_id),
    src_bytes                     INTEGER NOT NULL,
    dst_bytes                     INTEGER NOT NULL,
    land                          INTEGER NOT NULL,
    wrong_fragment                INTEGER NOT NULL,
    urgent                        INTEGER NOT NULL,
    hot                           INTEGER NOT NULL,
    num_failed_logins             INTEGER NOT NULL,
    logged_in                     INTEGER NOT NULL,
    num_compromised               INTEGER NOT NULL,
    root_shell                    INTEGER NOT NULL,
    su_attempted                  INTEGER NOT NULL,
    num_root                      INTEGER NOT NULL,
    num_file_creations            INTEGER NOT NULL,
    num_shells                    INTEGER NOT NULL,
    num_access_files              INTEGER NOT NULL,
    num_outbound_cmds             INTEGER NOT NULL,
    is_host_login                 INTEGER NOT NULL,
    is_guest_login                INTEGER NOT NULL,
    count                         INTEGER NOT NULL,
    srv_count                     INTEGER NOT NULL,
    serror_rate                   REAL    NOT NULL,
    srv_serror_rate               REAL    NOT NULL,
    rerror_rate                   REAL    NOT NULL,
    srv_rerror_rate               REAL    NOT NULL,
    same_srv_rate                 REAL    NOT NULL,
    diff_srv_rate                 REAL    NOT NULL,
    srv_diff_host_rate            REAL    NOT NULL,
    dst_host_count                INTEGER NOT NULL,
    dst_host_srv_count            INTEGER NOT NULL,
    dst_host_same_srv_rate        REAL    NOT NULL,
    dst_host_diff_srv_rate        REAL    NOT NULL,
    dst_host_same_src_port_rate   REAL    NOT NULL,
    dst_host_srv_diff_host_rate   REAL    NOT NULL,
    dst_host_serror_rate          REAL    NOT NULL,
    dst_host_srv_serror_rate      REAL    NOT NULL,
    dst_host_rerror_rate          REAL    NOT NULL,
    dst_host_srv_rerror_rate      REAL    NOT NULL,
    attack_id                     INTEGER NOT NULL REFERENCES attack_types(attack_id),
    difficulty                    INTEGER
);

CREATE INDEX IF NOT EXISTS idx_conn_split        ON connections(split);
CREATE INDEX IF NOT EXISTS idx_conn_protocol     ON connections(protocol_id);
CREATE INDEX IF NOT EXISTS idx_conn_service      ON connections(service_id);
CREATE INDEX IF NOT EXISTS idx_conn_flag         ON connections(flag_id);
CREATE INDEX IF NOT EXISTS idx_conn_attack       ON connections(attack_id);

-- View that joins the fact table to its dimensions, used by EDA / queries.
CREATE VIEW IF NOT EXISTS v_connections_full AS
SELECT
    c.conn_id, c.split,
    p.protocol_name AS protocol_type,
    s.service_name  AS service,
    f.flag_name     AS flag,
    a.attack_label  AS label,
    a.attack_family,
    a.is_attack,
    c.duration, c.src_bytes, c.dst_bytes, c.land, c.wrong_fragment,
    c.urgent, c.hot, c.num_failed_logins, c.logged_in, c.num_compromised,
    c.root_shell, c.su_attempted, c.num_root, c.num_file_creations,
    c.num_shells, c.num_access_files, c.num_outbound_cmds,
    c.is_host_login, c.is_guest_login, c.count, c.srv_count,
    c.serror_rate, c.srv_serror_rate, c.rerror_rate, c.srv_rerror_rate,
    c.same_srv_rate, c.diff_srv_rate, c.srv_diff_host_rate,
    c.dst_host_count, c.dst_host_srv_count, c.dst_host_same_srv_rate,
    c.dst_host_diff_srv_rate, c.dst_host_same_src_port_rate,
    c.dst_host_srv_diff_host_rate, c.dst_host_serror_rate,
    c.dst_host_srv_serror_rate, c.dst_host_rerror_rate,
    c.dst_host_srv_rerror_rate, c.difficulty
FROM connections c
JOIN protocols    p ON p.protocol_id = c.protocol_id
JOIN services     s ON s.service_id  = c.service_id
JOIN flags        f ON f.flag_id     = c.flag_id
JOIN attack_types a ON a.attack_id   = c.attack_id;
