-- Analytical queries used in the report and notebooks.
-- Run:   sqlite3 data/processed/ids.sqlite < sql/example_queries.sql

-- Q1. Connections per attack family in each split.
SELECT split, attack_family, COUNT(*) AS n
FROM v_connections_full
GROUP BY split, attack_family
ORDER BY split, n DESC;

-- Q2. Top 10 services targeted by attacks (training set).
SELECT service, COUNT(*) AS n_attacks
FROM v_connections_full
WHERE split = 'train' AND is_attack = 1
GROUP BY service
ORDER BY n_attacks DESC
LIMIT 10;

-- Q3. Average bytes for normal vs. malicious traffic, broken down by protocol.
SELECT protocol_type,
       attack_family,
       COUNT(*)                        AS n,
       ROUND(AVG(src_bytes), 2)        AS avg_src_bytes,
       ROUND(AVG(dst_bytes), 2)        AS avg_dst_bytes
FROM v_connections_full
WHERE split = 'train'
GROUP BY protocol_type, attack_family
ORDER BY protocol_type, attack_family;

-- Q4. Failed-login profile per attack family. Useful for R2L detection.
SELECT attack_family,
       ROUND(AVG(num_failed_logins), 3) AS avg_failed_logins,
       ROUND(AVG(logged_in),         3) AS pct_logged_in,
       ROUND(AVG(is_guest_login),    3) AS pct_guest
FROM v_connections_full
WHERE split = 'train'
GROUP BY attack_family;

-- Q5. Connection-rate features. Typical Probe / DoS signal.
SELECT attack_family,
       ROUND(AVG(count),         2) AS avg_count,
       ROUND(AVG(srv_count),     2) AS avg_srv_count,
       ROUND(AVG(serror_rate),   3) AS avg_serror_rate,
       ROUND(AVG(rerror_rate),   3) AS avg_rerror_rate
FROM v_connections_full
WHERE split = 'train'
GROUP BY attack_family;
