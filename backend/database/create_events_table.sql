-- =============================================================
-- Script: Create Events Table
-- Description: Creates the events table with all required fields
-- =============================================================

CREATE TABLE IF NOT EXISTS events (
    id              SERIAL PRIMARY KEY,
    keyword         VARCHAR(255)        NOT NULL,
    time_and_date   TIMESTAMP           NOT NULL,
    source          VARCHAR(255)        NOT NULL,
    event_id        VARCHAR(100)        UNIQUE NOT NULL,
    task_category   VARCHAR(100)        NOT NULL,

    created_at      TIMESTAMP           DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP           DEFAULT CURRENT_TIMESTAMP
);

-- =============================================================
-- Indexes for commonly queried columns
-- =============================================================

CREATE INDEX IF NOT EXISTS idx_events_keyword       ON events (keyword);
CREATE INDEX IF NOT EXISTS idx_events_time_and_date ON events (time_and_date);
CREATE INDEX IF NOT EXISTS idx_events_task_category ON events (task_category);
CREATE INDEX IF NOT EXISTS idx_events_event_id      ON events (event_id);

-- =============================================================
-- Sample insert for verification
-- =============================================================

-- INSERT INTO events (keyword, time_and_date, source, event_id, task_category)
-- VALUES ('system_alert', '2026-03-22 10:00:00', 'monitor_service', 'EVT-00001', 'infrastructure');
