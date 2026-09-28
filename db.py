import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
DB_PATH = Path(os.getenv("BNF_DB_PATH", "./banknifty.db")).resolve()


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS collection_runs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          center INTEGER NOT NULL, expiry TEXT NOT NULL,
          step INTEGER NOT NULL, sides INTEGER NOT NULL,
          status TEXT NOT NULL, started_at TEXT NOT NULL,
          completed_at TEXT, error TEXT
        );
        CREATE TABLE IF NOT EXISTS option_snapshots (
          id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER NOT NULL,
          symbol TEXT NOT NULL, strike INTEGER NOT NULL, option_type TEXT NOT NULL,
          open REAL, high REAL, low REAL, close REAL, volume REAL,
          cumulative_delta REAL, buy_volume REAL, sell_volume REAL,
          error TEXT, fetched_at TEXT NOT NULL,
          FOREIGN KEY(run_id) REFERENCES collection_runs(id)
        );
        CREATE INDEX IF NOT EXISTS idx_snapshots_run ON option_snapshots(run_id);
        """)


def create_run(center, expiry, step, sides):
    started = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO collection_runs(center,expiry,step,sides,status,started_at) VALUES(?,?,?,?,?,?)",
            (center, expiry, step, sides, "running", started),
        )
        return cur.lastrowid


def save_snapshot(run_id, item):
    with connect() as conn:
        conn.execute("""
        INSERT INTO option_snapshots(
          run_id,symbol,strike,option_type,open,high,low,close,volume,
          cumulative_delta,buy_volume,sell_volume,error,fetched_at
        ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
          run_id, item["symbol"], item["strike"], item["option_type"],
          item["open"], item["high"], item["low"], item["close"], item["volume"],
          item["cumulative_delta"], item["buy_volume"], item["sell_volume"],
          item.get("error"), item["fetched_at"],
        ))


def finish_run(run_id, status, error=None):
    completed = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute(
            "UPDATE collection_runs SET status=?,completed_at=?,error=? WHERE id=?",
            (status, completed, error, run_id),
        )


def rows_as_dicts(rows):
    return [dict(row) for row in rows]
