import json

from database.db import get_db_connection


def save_consultation(user, selected_symptoms, result):
    diagnosis = result.get("results", [None])[0] if result.get("results") else None
    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO consultation_history (
                user_id, username, selected_symptoms, status,
                disease_id, disease_name, score, solution
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["user_id"],
                user["username"],
                json.dumps(selected_symptoms, ensure_ascii=False),
                result["status"],
                diagnosis["disease_id"] if diagnosis else None,
                diagnosis["naran_moras"] if diagnosis else None,
                diagnosis["score"] if diagnosis else None,
                diagnosis.get("solusi", "") if diagnosis else "",
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_consultation_history(user_id=None, limit=500):
    conn = get_db_connection()
    try:
        if user_id is None and limit is None:
            rows = conn.execute(
                """
                SELECT history_id, username, selected_symptoms, status,
                       disease_id, disease_name, score, solution, created_at
                FROM consultation_history
                ORDER BY created_at DESC, history_id DESC
                """
            ).fetchall()
        elif user_id is not None and limit is None:
            rows = conn.execute(
                """
                SELECT history_id, username, selected_symptoms, status,
                       disease_id, disease_name, score, solution, created_at
                FROM consultation_history
                WHERE user_id = ?
                ORDER BY created_at DESC, history_id DESC
                """,
                (user_id,),
            ).fetchall()
        elif user_id is None:
            rows = conn.execute(
                """
                SELECT history_id, username, selected_symptoms, status,
                       disease_id, disease_name, score, solution, created_at
                FROM consultation_history
                ORDER BY created_at DESC, history_id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT history_id, username, selected_symptoms, status,
                       disease_id, disease_name, score, solution, created_at
                FROM consultation_history
                WHERE user_id = ?
                ORDER BY created_at DESC, history_id DESC LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        history = []
        for row in rows:
            item = dict(row)
            item["selected_symptoms"] = json.loads(item["selected_symptoms"])
            item["selected_symptoms_text"] = ", ".join(
                f"{symptom.get('code', '')} — {symptom.get('name', '')}".strip(" —")
                for symptom in item["selected_symptoms"]
            )
            item["result"] = item["disease_name"] or "Belum ada hasil"
            history.append(item)
        return history
    finally:
        conn.close()


def get_history_counts(user_id=None):
    conn = get_db_connection()
    try:
        if user_id is None:
            rows = conn.execute(
                "SELECT disease_name, COUNT(*) AS total FROM consultation_history "
                "WHERE status = 'success' GROUP BY disease_name ORDER BY total DESC"
            ).fetchall()
            total = conn.execute("SELECT COUNT(*) FROM consultation_history").fetchone()[0]
        else:
            rows = conn.execute(
                """
                SELECT disease_name, COUNT(*) AS total FROM consultation_history
                WHERE user_id = ? AND status = 'success'
                GROUP BY disease_name ORDER BY total DESC
                """,
                (user_id,),
            ).fetchall()
            total = conn.execute(
                "SELECT COUNT(*) FROM consultation_history WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
        return total, [dict(row) for row in rows]
    finally:
        conn.close()
