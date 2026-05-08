from sqlalchemy import text

from ids_pipeline.schema import get_engine


def test_database_has_expected_tables(built_db):
    _, url = built_db
    engine = get_engine(url)
    with engine.connect() as conn:
        names = {
            r[0]
            for r in conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
        }
    assert {"protocols", "services", "flags",
            "attack_types", "connections"}.issubset(names)


def test_view_joins_correctly(built_db):
    _, url = built_db
    engine = get_engine(url)
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT COUNT(*) FROM v_connections_full")
        ).scalar_one()
        n_attack = conn.execute(text(
            "SELECT COUNT(*) FROM v_connections_full WHERE attack_family != 'normal'"
        )).scalar_one()
    assert n > 0
    assert n_attack > 0


def test_attack_family_mapping_only_known_values(built_db):
    _, url = built_db
    engine = get_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT DISTINCT attack_family FROM attack_types"
        )).all()
    families = {r[0] for r in rows}
    assert families.issubset({"normal", "dos", "probe", "r2l", "u2r"})
