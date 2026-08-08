-- SQL alternative to test_base.json.
-- Run with: python py_dbase.py --crea test_base.sql

CREATE TABLE IF NOT EXISTS test (
    uid INTEGER PRIMARY KEY,
    selector TEXT,
    type TEXT,
    text TEXT,
    key TEXT
);
