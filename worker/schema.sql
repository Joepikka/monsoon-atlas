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

CREATE TABLE feed_checks (
  state TEXT NOT NULL CHECK(state='ka'),
  source_id TEXT NOT NULL CHECK(source_id IN ('S01','S09')),
  period_index INTEGER NOT NULL CHECK(period_index>=0),
  admitted_ms INTEGER NOT NULL CHECK(admitted_ms>=0),
  budget_day TEXT NOT NULL REFERENCES daily_usage(day),
  database_bytes INTEGER NOT NULL CHECK(database_bytes>=0),
  PRIMARY KEY(state,source_id,period_index)
);
CREATE INDEX feed_check_clock ON feed_checks(state,source_id,admitted_ms DESC);
CREATE TRIGGER feed_check_guard BEFORE INSERT ON feed_checks BEGIN
  SELECT CASE WHEN NEW.period_index<>CAST(NEW.admitted_ms /
    CASE NEW.source_id WHEN 'S01' THEN 21600000 ELSE 900000 END AS INTEGER)
    THEN RAISE(ABORT,'invalid_check_period') END;
  SELECT CASE WHEN EXISTS (
    SELECT 1 FROM feed_checks WHERE state=NEW.state AND source_id=NEW.source_id
    AND admitted_ms > NEW.admitted_ms - CASE NEW.source_id WHEN 'S01' THEN 21600000 ELSE 900000 END
  ) THEN RAISE(ABORT,'check_not_due') END;
  SELECT CASE WHEN MAX((SELECT allocated_bytes FROM capacity WHERE id=1),NEW.database_bytes)
    + 16384 > 400000000 THEN RAISE(ABORT,'storage_cap') END;
  SELECT CASE WHEN (SELECT writes_reserved FROM daily_usage WHERE day=NEW.budget_day)
    + 20 > 10000 THEN RAISE(ABORT,'write_cap') END;
END;
CREATE TRIGGER feed_check_account AFTER INSERT ON feed_checks BEGIN
  UPDATE capacity SET allocated_bytes=MAX(allocated_bytes,NEW.database_bytes)+16384 WHERE id=1;
  UPDATE daily_usage SET writes_reserved=writes_reserved+20 WHERE day=NEW.budget_day;
END;
CREATE TRIGGER hot_account AFTER INSERT ON hot_snapshots BEGIN
  UPDATE capacity SET allocated_bytes=MAX(allocated_bytes,NEW.database_bytes)+length(NEW.payload)+65536 WHERE id=1;
  UPDATE daily_usage SET writes_reserved=writes_reserved+20 WHERE day=NEW.budget_day;
  INSERT INTO hot_current(state,source_id,snapshot_id,as_of_ms) VALUES(NEW.state,NEW.source_id,NEW.id,NEW.as_of_ms)
  ON CONFLICT(state,source_id) DO UPDATE SET snapshot_id=excluded.snapshot_id,as_of_ms=excluded.as_of_ms
    WHERE excluded.as_of_ms>hot_current.as_of_ms;
END;

-- T260 (D95): trusted Ask chunks, loaded only by the deploy step from
-- atlas.rag.manifest. The Worker never writes them and serves only the
-- release named in ask_current.
CREATE TABLE ask_chunks (
  release TEXT NOT NULL CHECK(length(release)=64),
  chunk_id TEXT NOT NULL,
  doc_id TEXT NOT NULL,
  path TEXT NOT NULL,
  heading TEXT NOT NULL,
  text TEXT NOT NULL,
  available_at TEXT NOT NULL,
  expires_at TEXT,
  states TEXT NOT NULL,
  sha256 TEXT NOT NULL CHECK(length(sha256)=64),
  PRIMARY KEY(release,chunk_id)
);
CREATE TABLE ask_current (
  id INTEGER PRIMARY KEY CHECK(id=1),
  release TEXT NOT NULL CHECK(length(release)=64)
);
