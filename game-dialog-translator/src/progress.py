from __future__ import annotations

import sqlite3
import shutil
from datetime import datetime
from pathlib import Path

from .parser import ParsedLine
from .utils import file_hash

VALID_STATUS = {"pending", "translated", "skipped_no_separator", "error", "validated"}


def get_file_hash(path: Path) -> str:
    return file_hash(path)


class ProgressStore:
    def __init__(self, progress_dir: Path, source_file: Path):
        self.progress_dir = progress_dir
        self.source_file = source_file
        self.file_hash = get_file_hash(source_file)
        self.source_file_name = source_file.name
        self.db_path = progress_dir / f"{self.file_hash}.sqlite"
        self.conn = open_progress_store(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS progress(
            file_hash TEXT, source_file_name TEXT, line_number INTEGER, chinese_part TEXT,
            english_original TEXT, protected_english TEXT, portuguese_translation TEXT,
            status TEXT, error_message TEXT, updated_at TEXT, batch_number INTEGER, attempts INTEGER,
            characters_count INTEGER, provider TEXT, fallback_used INTEGER, provider_chain_attempted TEXT, characters_sent INTEGER, translated_at TEXT, original_line_ending TEXT, original_line TEXT,
            PRIMARY KEY(file_hash, line_number)
        )"""
        )
        self._migrate()
        self.conn.commit()

    def _migrate(self):
        cols = {r[1] for r in self.conn.execute("PRAGMA table_info(progress)").fetchall()}
        for name, typ in [("provider","TEXT"),("fallback_used","INTEGER"),("provider_chain_attempted","TEXT"),("characters_sent","INTEGER"),("translated_at","TEXT")]:
            if name not in cols:
                self.conn.execute(f"ALTER TABLE progress ADD COLUMN {name} {typ}")

    def initialize_progress(self, parsed_lines: list[ParsedLine]) -> None:
        self.save_batch(parsed_lines, batch_number=0)

    def load_progress(self):
        return self.conn.execute(
            "SELECT * FROM progress WHERE file_hash=? ORDER BY line_number", (self.file_hash,)
        ).fetchall()

    def apply_existing(self, parsed_lines: list[ParsedLine]) -> None:
        by_ln = {r["line_number"]: r for r in self.load_progress()}
        for l in parsed_lines:
            r = by_ln.get(l.line_number)
            if not r:
                continue
            l.status = r["status"]
            l.portuguese_translation = r["portuguese_translation"] or ""
            l.error_message = r["error_message"] or ""
            l.protected_english = r["protected_english"] or ""
            l.attempts = r["attempts"] or 0
            l.characters_count = r["characters_count"] or 0
            l.provider = r["provider"] if "provider" in r.keys() else ""

    def save_line(self, record: ParsedLine, batch_number: int = 0) -> None:
        self.save_batch([record], batch_number=batch_number)

    def save_batch(self, records: list[ParsedLine], batch_number: int = 0) -> None:
        now = datetime.utcnow().isoformat()
        for l in records:
            st = l.status if l.status in VALID_STATUS else "error"
            self.conn.execute(
                """INSERT INTO progress VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(file_hash,line_number) DO UPDATE SET
            chinese_part=excluded.chinese_part, english_original=excluded.english_original,
            protected_english=excluded.protected_english, portuguese_translation=excluded.portuguese_translation,
            status=excluded.status, error_message=excluded.error_message, updated_at=excluded.updated_at,
            batch_number=excluded.batch_number, attempts=excluded.attempts, characters_count=excluded.characters_count,
            provider=excluded.provider, fallback_used=excluded.fallback_used, provider_chain_attempted=excluded.provider_chain_attempted, characters_sent=excluded.characters_sent, translated_at=excluded.translated_at, original_line_ending=excluded.original_line_ending, original_line=excluded.original_line""",
                (
                    self.file_hash,
                    self.source_file_name,
                    l.line_number,
                    l.chinese_part,
                    l.english_part,
                    l.protected_english,
                    l.portuguese_translation,
                    st,
                    l.error_message,
                    now,
                    batch_number,
                    l.attempts,
                    l.characters_count,
                    getattr(l, "provider", ""),
                    int(bool(getattr(l, "fallback_used", False))),
                    str(getattr(l, "provider_chain_attempted", "")),
                    getattr(l, "characters_sent", l.characters_count),
                    getattr(l, "translated_at", now),
                    l.original_line_ending,
                    l.original_line,
                ),
            )
        self.conn.commit()

    def get_summary(self) -> dict:
        rows = self.load_progress()
        updated_at = max((r["updated_at"] for r in rows if r["updated_at"]), default="")
        return {
            "total_lines": len(rows),
            "translatable_lines": sum(1 for r in rows if r["chinese_part"] != "" or r["english_original"] != ""),
            "translated_lines": sum(1 for r in rows if r["status"] == "translated"),
            "pending_lines": sum(1 for r in rows if r["status"] == "pending"),
            "error_lines": sum(1 for r in rows if r["status"] == "error"),
            "skipped_lines": sum(1 for r in rows if r["status"] == "skipped_no_separator"),
            "characters_translated": sum((r["characters_count"] or 0) for r in rows if r["status"] == "translated"),
            "updated_at": updated_at,
        }

    def reset_progress(self) -> None:
        self.conn.execute("DELETE FROM progress WHERE file_hash=?", (self.file_hash,))
        self.conn.commit()

    def mark_errors_for_retry(self) -> int:
        cur = self.conn.execute(
            "UPDATE progress SET status='pending', error_message='' WHERE file_hash=? AND status='error'",
            (self.file_hash,),
        )
        self.conn.commit()
        return cur.rowcount

    def backup(self) -> Path | None:
        if not self.db_path.exists():
            return None
        backup_dir = self.progress_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        backup_path = backup_dir / f"{self.file_hash}_{timestamp}.sqlite"
        self.conn.commit()
        shutil.copy2(self.db_path, backup_path)
        return backup_path


def open_progress_store(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(db_path)
