import csv
from pathlib import Path
from db import get_db_connection
from weighting import derive_symptom_weights
from guidance import load_guidance

BASE_DIR = Path(__file__).resolve().parent
DATASET_DIR = BASE_DIR / "dataset"


def read_csv(filename):
    file_path = DATASET_DIR / filename

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def seed_diseases(conn):
    rows = read_csv("diseases.csv")
    guidance = load_guidance()

    conn.executemany("""
        INSERT INTO diseases (
            disease_id,
            naran_moras,
            deskrisaun,
            severidade,
            transmite,
            fonte
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (
            row["disease_id"],
            row["naran_moras"],
            row["deskrisaun"],
            row["severidade"],
            row["transmite"],
            row["fonte"]
        )
        for row in rows
    ])

    conn.executemany(
        "UPDATE diseases SET rekomendasaun = ?, rekomendasaun_url = ? WHERE disease_id = ?",
        [
            (item["recommendation"], item["source_url"], disease_id)
            for disease_id, item in guidance.items()
        ],
    )

    print(f"Diseases: {len(rows)}")


def seed_symptoms(conn):
    rows = read_csv("symptoms.csv")
    rules = read_csv("rules.csv")
    weights = derive_symptom_weights(
        [row["symptom_id"] for row in rows],
        [{"conditions": row["conditions"], "conclusion": row["conclusion"]} for row in rules],
    )

    conn.executemany("""
        INSERT INTO symptoms (
            symptom_id,
            kode_sintoma,
            naran_sintoma,
            deskrisaun,
            area_kulit,
            bobot
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (
            row["symptom_id"],
            row["kode_sintoma"],
            row["naran_sintoma"],
            row["deskrisaun"],
            row["area_kulit"],
            weights[row["symptom_id"]]
        )
        for row in rows
    ])

    print(f"Symptoms: {len(rows)}")


def seed_rules(conn):
    rows = read_csv("rules.csv")

    conn.executemany("""
        INSERT INTO rules (
            rule_id,
            disease_id,
            conditions,
            conclusion,
            priority
        )
        VALUES (?, ?, ?, ?, ?)
    """, [
        (
            row["rule_id"],
            row["disease_id"],
            row["conditions"],
            row["conclusion"],
            int(row["priority"])
        )
        for row in rows
    ])

    print(f"Rules: {len(rows)}")


def seed_sources(conn):
    rows = read_csv("sources.csv")

    conn.executemany("""
        INSERT INTO sources (
            source_id,
            disease_id,
            source_name,
            source_type,
            reference_title,
            url
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        (
            row["source_id"],
            row["disease_id"],
            row["source_name"],
            row["source_type"],
            row["reference_title"],
            row["url"]
        )
        for row in rows
    ])

    print(f"Sources: {len(rows)}")


def seed_database():
    conn = get_db_connection()

    try:
        # Kosongkan data lama
        conn.execute("DELETE FROM sources")
        conn.execute("DELETE FROM rules")
        conn.execute("DELETE FROM symptoms")
        conn.execute("DELETE FROM diseases")

        # Masukkan data baru
        seed_diseases(conn)
        seed_symptoms(conn)
        seed_rules(conn)
        seed_sources(conn)

        conn.commit()

        print()
        print("================================")
        print("DATABASE SEED BERHASIL")
        print("================================")

    except Exception as e:
        conn.rollback()
        print("ERROR:", e)

    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
