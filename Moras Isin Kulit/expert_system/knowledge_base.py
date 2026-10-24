from database.db import get_db_connection


def get_all_symptoms():
    conn = get_db_connection()

    try:
        rows = conn.execute("""
            SELECT
                kd_sintoma AS symptom_id,
                kd_sintoma AS kode_sintoma,
                naran AS naran_sintoma,
                bobot
            FROM sintoma
            ORDER BY kd_sintoma
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_all_diseases():
    conn = get_db_connection()

    try:
        rows = conn.execute("""
            SELECT kd_problema AS disease_id, naran AS naran_moras, solusi
            FROM problema
            ORDER BY kd_problema
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_all_rules():
    conn = get_db_connection()

    try:
        rows = conn.execute("""
            SELECT
                rule_id,
                disease_id,
                conditions,
                conclusion,
                priority
            FROM rules
            ORDER BY priority, rule_id
        """).fetchall()

        return [dict(row) for row in rows]

    finally:
        conn.close()


def get_disease_by_id(disease_id):
    conn = get_db_connection()

    try:
        row = conn.execute("""
            SELECT kd_problema AS disease_id, naran AS naran_moras, solusi
            FROM problema
            WHERE kd_problema = ?
        """, (disease_id,)).fetchone()

        return dict(row) if row else None

    finally:
        conn.close()
