from __future__ import annotations
import sqlite3
from datetime import datetime
from pathlib import Path
from .parser import ParsedLine
from .utils import file_hash

VALID_STATUS = {"pending","translated","skipped_no_separator","error","validated"}

class ProgressStore:
    def __init__(self, progress_dir: Path, source_file: Path):
        self.file_hash = file_hash(source_file)
        self.db_path = progress_dir / f"{self.file_hash}.sqlite"
        self.source_file_name = source_file.name
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self):
        self.conn.execute("""CREATE TABLE IF NOT EXISTS progress(
            file_hash TEXT, source_file_name TEXT, line_number INTEGER, chinese_part TEXT,
            english_original TEXT, protected_english TEXT, portuguese_translation TEXT,
            status TEXT, error_message TEXT, updated_at TEXT, batch_number INTEGER, attempts INTEGER,
            characters_count INTEGER, original_line_ending TEXT, original_line TEXT,
            PRIMARY KEY(file_hash, line_number)
        )""")
        self.conn.commit()

    def upsert_lines(self, lines: list[ParsedLine], batch_number: int = 0):
        now = datetime.utcnow().isoformat()
        for l in lines:
            st = l.status if l.status in VALID_STATUS else "error"
            self.conn.execute("""INSERT INTO progress VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(file_hash,line_number) DO UPDATE SET
            chinese_part=excluded.chinese_part, english_original=excluded.english_original,
            protected_english=excluded.protected_english, portuguese_translation=excluded.portuguese_translation,
            status=excluded.status, error_message=excluded.error_message, updated_at=excluded.updated_at,
            batch_number=excluded.batch_number, attempts=excluded.attempts, characters_count=excluded.characters_count,
            original_line_ending=excluded.original_line_ending, original_line=excluded.original_line""",
            (self.file_hash, self.source_file_name, l.line_number, l.chinese_part, l.english_part, l.protected_english,
             l.portuguese_translation, st, l.error_message, now, batch_number, l.attempts, l.characters_count,
             l.original_line_ending, l.original_line))
        self.conn.commit()

    def apply_existing(self, lines: list[ParsedLine]):
        by_ln = {r["line_number"]: r for r in self.get_lines()}
        for l in lines:
            r = by_ln.get(l.line_number)
            if not r: continue
            l.status = r["status"]
            l.portuguese_translation = r["portuguese_translation"] or ""
            l.error_message = r["error_message"] or ""
            l.protected_english = r["protected_english"] or ""
            l.attempts = r["attempts"] or 0
            l.characters_count = r["characters_count"] or 0

    def get_lines(self):
        return self.conn.execute("SELECT * FROM progress WHERE file_hash=? ORDER BY line_number", (self.file_hash,)).fetchall()
