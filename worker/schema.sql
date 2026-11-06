PRAGMA foreign_keys = ON;

CREATE TABLE capacity (
  id INTEGER PRIMARY KEY CHECK(id=1),
  allocated_bytes INTEGER NOT NULL CHECK(allocated_bytes>=0)
);
INSERT INTO capacity VALUES (1,0);
CREATE TABLE daily_usage (
  day TEXT PRIMARY KEY,
  writes_reserved INTEGER NOT NULL CHECK(writes_reserved BETWEEN 0 AND 10000)
);
CREATE TABLE hot_snapshots (
  id TEXT PRIMARY KEY CHECK(length(id)=64),
  state TEXT NOT NULL CHECK(state='ka'),
  source_id TEXT NOT NULL CHECK(source_id IN ('S01','S09')),
  as_of_ms INTEGER NOT NULL,
  payload BLOB NOT NULL CHECK(length(payload)<=1048576),
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  budget_day TEXT NOT NULL REFERENCES daily_usage(day),
  database_bytes INTEGER NOT NULL CHECK(database_bytes>=0),
  UNIQUE(state,source_id,as_of_ms)
);
CREATE TABLE hot_current (
  state TEXT NOT NULL,
  source_id TEXT NOT NULL,
  snapshot_id TEXT NOT NULL REFERENCES hot_snapshots(id),
  as_of_ms INTEGER NOT NULL,
  PRIMARY KEY(state,source_id)
);

-- Reserve 20 D1 row/index writes and payload bytes + 64 KiB per new snapshot.
-- Both guards and all head/counter changes are in the insert transaction.
CREATE TRIGGER hot_guard BEFORE INSERT ON hot_snapshots BEGIN
  SELECT CASE WHEN MAX((SELECT allocated_bytes FROM capacity WHERE id=1),NEW.database_bytes)
    + length(NEW.payload) + 65536 > 400000000 THEN RAISE(ABORT,'storage_cap') END;
  SELECT CASE WHEN (SELECT writes_reserved FROM daily_usage WHERE day=NEW.budget_day)
    + 20 > 10000 THEN RAISE(ABORT,'write_cap') END;
END;
CREATE TRIGGER hot_account AFTER INSERT ON hot_snapshots BEGIN
  UPDATE capacity SET allocated_bytes=MAX(allocated_bytes,NEW.database_bytes)+length(NEW.payload)+65536 WHERE id=1;
  UPDATE daily_usage SET writes_reserved=writes_reserved+20 WHERE day=NEW.budget_day;
  INSERT INTO hot_current(state,source_id,snapshot_id,as_of_ms) VALUES(NEW.state,NEW.source_id,NEW.id,NEW.as_of_ms)
  ON CONFLICT(state,source_id) DO UPDATE SET snapshot_id=excluded.snapshot_id,as_of_ms=excluded.as_of_ms
    WHERE excluded.as_of_ms>hot_current.as_of_ms;
END;
