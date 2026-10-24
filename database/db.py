import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "skin_expert.db"


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS consultation_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT NOT NULL,
            selected_symptoms TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('success', 'no_result')),
            disease_id TEXT,
            disease_name TEXT,
            score INTEGER,
            solution TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_user_date ON consultation_history(user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_history_date ON consultation_history(created_at)")
    disease_columns = {row["name"] for row in conn.execute("PRAGMA table_info(diseases)")}
    added_guidance_fields = []
    if disease_columns and "rekomendasaun" not in disease_columns:
        conn.execute("ALTER TABLE diseases ADD COLUMN rekomendasaun TEXT NOT NULL DEFAULT ''")
        added_guidance_fields.append("rekomendasaun")
    if disease_columns and "rekomendasaun_url" not in disease_columns:
        conn.execute("ALTER TABLE diseases ADD COLUMN rekomendasaun_url TEXT NOT NULL DEFAULT ''")
        added_guidance_fields.append("rekomendasaun_url")
    if added_guidance_fields:
        from database.guidance import load_guidance

        guidance = load_guidance()
        conn.executemany(
            "UPDATE diseases SET rekomendasaun = ?, rekomendasaun_url = ? WHERE disease_id = ?",
            [
                (item["recommendation"], item["source_url"], disease_id)
                for disease_id, item in guidance.items()
            ],
        )
    # Guarantee that every seeded disease has a useful solution, including
    # databases where the guidance columns existed but were left blank.
    if disease_columns:
        from database.guidance import load_guidance

        guidance = load_guidance()
        conn.executemany(
            """
            UPDATE diseases
            SET rekomendasaun = ?, rekomendasaun_url = ?
            WHERE disease_id = ? AND TRIM(COALESCE(rekomendasaun, '')) = ''
            """,
            [
                (item["recommendation"], item["source_url"], disease_id)
                for disease_id, item in guidance.items()
            ],
        )
    symptom_columns = {row["name"] for row in conn.execute("PRAGMA table_info(symptoms)")}
    if symptom_columns and "bobot" not in symptom_columns:
        conn.execute("ALTER TABLE symptoms ADD COLUMN bobot REAL NOT NULL DEFAULT 0.25")
        from database.weighting import derive_symptom_weights

        if "weight" in symptom_columns:
            conn.execute("UPDATE symptoms SET bobot = CAST(weight AS REAL) / 5.0")
        else:
            symptom_ids = [row[0] for row in conn.execute("SELECT symptom_id FROM symptoms")]
            rules = [dict(row) for row in conn.execute("SELECT conditions, conclusion FROM rules")]
            bobot_values = derive_symptom_weights(symptom_ids, rules)
            conn.executemany(
                "UPDATE symptoms SET bobot = ? WHERE symptom_id = ?",
                [(bobot, symptom_id) for symptom_id, bobot in bobot_values.items()],
            )
    # Replace the earlier views with physical tables matching the requested schema.
    objects = {row["name"]: row["type"] for row in conn.execute(
        "SELECT name, type FROM sqlite_master WHERE name IN ('problema', 'sintoma')"
    )}
    if objects.get("problema") == "view":
        conn.execute("DROP VIEW problema")
    if objects.get("sintoma") == "view":
        conn.execute("DROP VIEW sintoma")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS problema (
            kd_problema TEXT PRIMARY KEY,
            naran TEXT NOT NULL,
            solusi TEXT NOT NULL DEFAULT ''
        )
    """)
    sintoma_columns = {row["name"]: row for row in conn.execute("PRAGMA table_info(sintoma)")}
    if sintoma_columns and str(sintoma_columns.get("bobot", {"type": ""})["type"]).upper() != "REAL":
        old_symptoms = [dict(row) for row in conn.execute(
            "SELECT kd_sintoma, naran, bobot FROM sintoma"
        )]
        conn.execute("ALTER TABLE sintoma RENAME TO sintoma_old")
        conn.execute("""
            CREATE TABLE sintoma (
                kd_sintoma TEXT PRIMARY KEY,
                naran TEXT NOT NULL,
                bobot REAL NOT NULL DEFAULT 0.25 CHECK (bobot > 0 AND bobot <= 1)
            )
        """)
        from database.weighting import derive_symptom_weights

        symptom_ids = [row[0] for row in conn.execute("SELECT symptom_id FROM symptoms")]
        rules = [dict(row) for row in conn.execute("SELECT conditions, conclusion FROM rules")]
        calculated_weights = derive_symptom_weights(symptom_ids, rules)
        conn.executemany(
            "INSERT INTO sintoma (kd_sintoma, naran, bobot) VALUES (?, ?, ?)",
            [
                (
                    row["kd_sintoma"],
                    row["naran"],
                    calculated_weights.get(
                        row["kd_sintoma"],
                        max(0.25, min(1.0, float(row["bobot"]) / 5)),
                    ),
                )
                for row in old_symptoms
            ],
        )
        conn.execute("DROP TABLE sintoma_old")
    else:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sintoma (
                kd_sintoma TEXT PRIMARY KEY,
                naran TEXT NOT NULL,
                bobot REAL NOT NULL DEFAULT 0.25 CHECK (bobot > 0 AND bobot <= 1)
            )
        """)
    conn.execute("""
        INSERT INTO problema (kd_problema, naran, solusi)
        SELECT disease_id, naran_moras, rekomendasaun FROM diseases WHERE 1
        ON CONFLICT(kd_problema) DO UPDATE SET
            naran = excluded.naran, solusi = excluded.solusi
    """)
    conn.execute("""
        INSERT INTO sintoma (kd_sintoma, naran, bobot)
        SELECT symptom_id, naran_sintoma, bobot
        FROM symptoms WHERE 1
        ON CONFLICT(kd_sintoma) DO UPDATE SET
            naran = excluded.naran
    """)
    conn.executescript("""
        CREATE TRIGGER IF NOT EXISTS sync_problem_insert AFTER INSERT ON diseases BEGIN
            INSERT INTO problema (kd_problema, naran, solusi)
            VALUES (NEW.disease_id, NEW.naran_moras, NEW.rekomendasaun)
            ON CONFLICT(kd_problema) DO UPDATE SET naran=excluded.naran, solusi=excluded.solusi;
        END;
        CREATE TRIGGER IF NOT EXISTS sync_problem_update AFTER UPDATE OF disease_id, naran_moras, rekomendasaun ON diseases BEGIN
            INSERT INTO problema (kd_problema, naran, solusi)
            VALUES (NEW.disease_id, NEW.naran_moras, NEW.rekomendasaun)
            ON CONFLICT(kd_problema) DO UPDATE SET naran=excluded.naran, solusi=excluded.solusi;
        END;
        CREATE TRIGGER IF NOT EXISTS sync_problem_delete AFTER DELETE ON diseases BEGIN
            DELETE FROM problema WHERE kd_problema = OLD.disease_id;
        END;
        DROP TRIGGER IF EXISTS sync_symptom_insert;
        DROP TRIGGER IF EXISTS sync_symptom_update;
        CREATE TRIGGER sync_symptom_insert AFTER INSERT ON symptoms BEGIN
            INSERT INTO sintoma (kd_sintoma, naran, bobot)
            VALUES (NEW.symptom_id, NEW.naran_sintoma,
                NEW.bobot)
            ON CONFLICT(kd_sintoma) DO UPDATE SET naran=excluded.naran;
        END;
        CREATE TRIGGER sync_symptom_update AFTER UPDATE OF symptom_id, naran_sintoma, bobot ON symptoms BEGIN
            INSERT INTO sintoma (kd_sintoma, naran, bobot)
            VALUES (NEW.symptom_id, NEW.naran_sintoma,
                NEW.bobot)
            ON CONFLICT(kd_sintoma) DO UPDATE SET naran=excluded.naran;
        END;
        CREATE TRIGGER IF NOT EXISTS sync_symptom_delete AFTER DELETE ON symptoms BEGIN
            DELETE FROM sintoma WHERE kd_sintoma = OLD.symptom_id;
        END;
    """)
    conn.commit()
    return conn


def init_database():
    schema_path = BASE_DIR / "schema.sql"

    with open(schema_path, "r", encoding="utf-8") as file:
        schema = file.read()

    conn = get_db_connection()

    try:
        conn.executescript(schema)
        conn.commit()
        print("Database berhasil dibuat.")
    finally:
        conn.close()


if __name__ == "__main__":
    init_database()
