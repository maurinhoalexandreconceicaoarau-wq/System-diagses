PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('admin', 'user')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

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
);

CREATE INDEX IF NOT EXISTS idx_history_user_date
ON consultation_history(user_id, created_at);

CREATE INDEX IF NOT EXISTS idx_history_date
ON consultation_history(created_at);

DROP TABLE IF EXISTS sources;
DROP TABLE IF EXISTS rules;
DROP TABLE IF EXISTS sintoma;
DROP TABLE IF EXISTS problema;
DROP TABLE IF EXISTS symptoms;
DROP TABLE IF EXISTS diseases;

CREATE TABLE diseases (
    disease_id TEXT PRIMARY KEY,
    naran_moras TEXT NOT NULL,
    deskrisaun TEXT NOT NULL,
    severidade TEXT NOT NULL,
    transmite TEXT NOT NULL,
    fonte TEXT,
    rekomendasaun TEXT NOT NULL DEFAULT '',
    rekomendasaun_url TEXT NOT NULL DEFAULT ''
);

CREATE TABLE symptoms (
    symptom_id TEXT PRIMARY KEY,
    kode_sintoma TEXT NOT NULL UNIQUE,
    naran_sintoma TEXT NOT NULL,
    deskrisaun TEXT NOT NULL,
    area_kulit TEXT,
    bobot REAL NOT NULL DEFAULT 0.25 CHECK (bobot > 0 AND bobot <= 1)
);

CREATE TABLE rules (
    rule_id TEXT PRIMARY KEY,
    disease_id TEXT NOT NULL,
    conditions TEXT NOT NULL,
    conclusion TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 1,

    FOREIGN KEY (disease_id)
        REFERENCES diseases(disease_id),

    FOREIGN KEY (conclusion)
        REFERENCES diseases(disease_id)
);

CREATE TABLE sources (
    source_id TEXT PRIMARY KEY,
    disease_id TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_type TEXT,
    reference_title TEXT,
    url TEXT,

    FOREIGN KEY (disease_id)
        REFERENCES diseases(disease_id)
);

CREATE INDEX idx_rules_disease
ON rules(disease_id);

CREATE INDEX idx_sources_disease
ON sources(disease_id);

CREATE TABLE problema (
    kd_problema TEXT PRIMARY KEY,
    naran TEXT NOT NULL,
    solusi TEXT NOT NULL DEFAULT ''
);

CREATE TABLE sintoma (
    kd_sintoma TEXT PRIMARY KEY,
    naran TEXT NOT NULL,
    bobot REAL NOT NULL DEFAULT 0.25 CHECK (bobot > 0 AND bobot <= 1)
);

INSERT INTO problema (kd_problema, naran, solusi)
SELECT disease_id, naran_moras, rekomendasaun FROM diseases;

INSERT INTO sintoma (kd_sintoma, naran, bobot)
SELECT symptom_id, naran_sintoma, bobot FROM symptoms;

CREATE TRIGGER sync_problem_insert AFTER INSERT ON diseases BEGIN
    INSERT INTO problema (kd_problema, naran, solusi)
    VALUES (NEW.disease_id, NEW.naran_moras, NEW.rekomendasaun)
    ON CONFLICT(kd_problema) DO UPDATE SET naran=excluded.naran, solusi=excluded.solusi;
END;
CREATE TRIGGER sync_problem_update AFTER UPDATE OF disease_id, naran_moras, rekomendasaun ON diseases BEGIN
    INSERT INTO problema (kd_problema, naran, solusi)
    VALUES (NEW.disease_id, NEW.naran_moras, NEW.rekomendasaun)
    ON CONFLICT(kd_problema) DO UPDATE SET naran=excluded.naran, solusi=excluded.solusi;
END;
CREATE TRIGGER sync_problem_delete AFTER DELETE ON diseases BEGIN
    DELETE FROM problema WHERE kd_problema = OLD.disease_id;
END;
CREATE TRIGGER sync_symptom_insert AFTER INSERT ON symptoms BEGIN
    INSERT INTO sintoma (kd_sintoma, naran, bobot)
    VALUES (NEW.symptom_id, NEW.naran_sintoma,
        NEW.bobot)
    ON CONFLICT(kd_sintoma) DO UPDATE SET naran=excluded.naran, bobot=excluded.bobot;
END;
CREATE TRIGGER sync_symptom_update AFTER UPDATE OF symptom_id, naran_sintoma, bobot ON symptoms BEGIN
    INSERT INTO sintoma (kd_sintoma, naran, bobot)
    VALUES (NEW.symptom_id, NEW.naran_sintoma,
        NEW.bobot)
    ON CONFLICT(kd_sintoma) DO UPDATE SET naran=excluded.naran;
END;
CREATE TRIGGER sync_symptom_delete AFTER DELETE ON symptoms BEGIN
    DELETE FROM sintoma WHERE kd_sintoma = OLD.symptom_id;
END;
