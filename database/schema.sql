
CREATE TABLE IF NOT EXISTS cohorts (
    id SERIAL PRIMARY KEY,
    name TEXT,
    shock_week INTEGER,
    shock_severity REAL
);

CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    name TEXT,
    cohort_id INTEGER,
    capital REAL,
    week INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS history (
    id SERIAL PRIMARY KEY,
    player_id INTEGER,
    week INTEGER,
    capital REAL
);
