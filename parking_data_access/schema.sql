-- Pilot parking data store, from the SPEC.md Data Contract.
-- Section 3: pilot lot and space metadata. Section 1: simulated sensor events.
-- Section 2 (15-minute modeling table) and section 4 (rule table) are not
-- stored yet; see docs/deployment.md. Section 5 trip records are personal
-- data under SR-04 and are not kept here.

CREATE TABLE IF NOT EXISTS lots (
    lot_id       TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    latitude     REAL NOT NULL,
    longitude    REAL NOT NULL,
    source_type  TEXT NOT NULL,
    reviewed_at  TEXT NOT NULL
);

-- capacity_by_zone counts distinct physical spaces; the zone sum is the lot's capacity.
CREATE TABLE IF NOT EXISTS lot_zone_capacity (
    lot_id    TEXT NOT NULL REFERENCES lots (lot_id),
    zone      TEXT NOT NULL,
    capacity  INTEGER NOT NULL CHECK (capacity >= 0),
    PRIMARY KEY (lot_id, zone)
);

-- A space_id belongs to exactly one lot and one physical zone.
CREATE TABLE IF NOT EXISTS spaces (
    space_id  TEXT PRIMARY KEY,
    lot_id    TEXT NOT NULL,
    zone      TEXT NOT NULL,
    FOREIGN KEY (lot_id, zone) REFERENCES lot_zone_capacity (lot_id, zone)
);

-- One row per accepted observation. observed_epoch is the observation time
-- (not the receive time) as UTC seconds, so instants compare across offsets.
-- The primary key drops duplicate events.
CREATE TABLE IF NOT EXISTS sensor_events (
    space_id        TEXT NOT NULL REFERENCES spaces (space_id),
    lot_id          TEXT NOT NULL,
    zone            TEXT NOT NULL,
    status          TEXT NOT NULL CHECK (status IN ('occupied', 'vacant')),
    timestamp       TEXT NOT NULL,
    observed_epoch  REAL NOT NULL,
    PRIMARY KEY (space_id, observed_epoch)
);

-- Rejected events are recorded, not silently dropped or turned into vacant spaces.
CREATE TABLE IF NOT EXISTS rejected_events (
    received_at  TEXT NOT NULL,
    space_id     TEXT,
    reason       TEXT NOT NULL
);
