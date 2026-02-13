
CREATE TABLE IF NOT EXISTS cohorts (
    id SERIAL PRIMARY KEY,
    name TEXT,
    shock_week INTEGER,
    shock_severity REAL,
    is_closed BOOLEAN DEFAULT FALSE
);

ALTER TABLE cohorts ADD COLUMN IF NOT EXISTS is_closed BOOLEAN DEFAULT FALSE;

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


CREATE INDEX IF NOT EXISTS idx_players_cohort ON players(cohort_id);
CREATE INDEX IF NOT EXISTS idx_history_player ON history(player_id);
