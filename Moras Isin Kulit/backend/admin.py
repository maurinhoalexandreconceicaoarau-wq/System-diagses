from database.db import get_db_connection


TABLES = {
    "Moras": {
        "table": "problema", "key": "kd_problema",
        "fields": ["kd_problema", "naran", "solusi"],
        "labels": ["Kode problema", "Nama penyakit", "Solusi"],
    },
    "Sintoma": {
        "table": "sintoma", "key": "kd_sintoma",
        "fields": ["kd_sintoma", "naran", "bobot"],
        "labels": ["ID sintoma", "Kode", "Naran", "Deskrisaun", "Área kulit", "Bobot global (0.01-1.00)"],
    },
    "Regra": {
        "table": "rules", "key": "rule_id",
        "fields": ["rule_id", "disease_id", "conditions", "conclusion", "priority"],
        "labels": ["ID regra", "Moras", "Kondisaun (kode AND kode)", "Konkluzaun (ID moras)", "Prioridade"],
    },
    "Fonte": {
        "table": "sources", "key": "source_id",
        "fields": ["source_id", "disease_id", "source_name", "source_type", "reference_title", "url"],
        "labels": ["ID fonte", "Moras", "Naran fonte", "Tipu", "Títulu referénsia", "URL"],
    },
}

TABLES["Sintoma"]["labels"] = ["Kode gejala", "Nama gejala", "Bobot (0.01-1.00)"]
TABLES.pop("Fonte", None)


def list_rows(table_name):
    config = TABLES[table_name]
    columns = ", ".join(config["fields"])
    conn = get_db_connection()
    try:
        return [dict(row) for row in conn.execute(f"SELECT {columns} FROM {config['table']} ORDER BY {config['key']}")]
    finally:
        conn.close()


def save_row(table_name, values, original_key=None):
    config = TABLES[table_name]
    fields = config["fields"]
    table = config["table"]
    key = config["key"]
    values = dict(values)
    for name in fields:
        if isinstance(values.get(name), str):
            values[name] = values[name].strip()
    optional_fields = {"solusi"}
    if any(values.get(name) in (None, "") for name in fields if name not in optional_fields):
        raise ValueError("Favor prense kampu hotu.")
    if table_name == "Regra":
        values["priority"] = int(values["priority"])
        values["conclusion"] = values["conclusion"].strip()
    if table_name == "Sintoma":
        values["bobot"] = float(values["bobot"])
        if not 0.01 <= values["bobot"] <= 1.0:
            raise ValueError("Bobot gejala harus antara 0.01 dan 1.00.")
    conn = get_db_connection()
    try:
        if original_key is None:
            columns = ", ".join(fields)
            marks = ", ".join("?" for _ in fields)
            conn.execute(f"INSERT INTO {table} ({columns}) VALUES ({marks})", [values[field] for field in fields])
        else:
            update_fields = [field for field in fields if field != key]
            assignments = ", ".join(f"{field} = ?" for field in update_fields)
            conn.execute(
                f"UPDATE {table} SET {assignments} WHERE {key} = ?",
                [values[field] for field in update_fields] + [original_key],
            )
        if table_name == "Moras":
            # Compatibility record required by the existing rules foreign key.
            conn.execute("""
                INSERT INTO diseases (disease_id, naran_moras, deskrisaun, severidade,
                    transmite, fonte, rekomendasaun, rekomendasaun_url)
                VALUES (?, ?, '', 'Médiu', 'Lae', '', ?, '')
                ON CONFLICT(disease_id) DO UPDATE SET
                    naran_moras=excluded.naran_moras,
                    rekomendasaun=excluded.rekomendasaun
            """, (values["kd_problema"], values["naran"], values["solusi"]))
        elif table_name == "Sintoma":
            conn.execute("""
                INSERT INTO symptoms (symptom_id, kode_sintoma, naran_sintoma,
                    deskrisaun, area_kulit, bobot)
                VALUES (?, ?, ?, '', '', ?)
                ON CONFLICT(symptom_id) DO UPDATE SET
                    kode_sintoma=excluded.kode_sintoma,
                    naran_sintoma=excluded.naran_sintoma,
                    bobot=excluded.bobot
            """, (values["kd_sintoma"], values["kd_sintoma"], values["naran"], values["bobot"]))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_row(table_name, key_value):
    config = TABLES[table_name]
    conn = get_db_connection()
    try:
        conn.execute(f"DELETE FROM {config['table']} WHERE {config['key']} = ?", (key_value,))
        if table_name == "Moras":
            conn.execute("DELETE FROM diseases WHERE disease_id = ?", (key_value,))
        elif table_name == "Sintoma":
            conn.execute("DELETE FROM symptoms WHERE symptom_id = ?", (key_value,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def list_users():
    conn = get_db_connection()
    try:
        return [dict(row) for row in conn.execute(
            "SELECT user_id, username, role, created_at FROM users ORDER BY user_id"
        )]
    finally:
        conn.close()


def update_user_role(user_id, role):
    if role not in ("admin", "user"):
        raise ValueError("Role la validu.")
    conn = get_db_connection()
    try:
        if role != "admin":
            admins = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
            current_role = conn.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if current_role and current_role["role"] == "admin" and admins <= 1:
                raise ValueError("Tenke iha admin ida nafatin.")
        conn.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_user(user_id):
    conn = get_db_connection()
    try:
        current = conn.execute("SELECT role FROM users WHERE user_id = ?", (user_id,)).fetchone()
        admins = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0]
        if current and current["role"] == "admin" and admins <= 1:
            raise ValueError("Labele hamos admin ikus liu.")
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
