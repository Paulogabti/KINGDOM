from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable
from .parser import ParsedLine


class ProgressStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.conn.execute("""CREATE TABLE IF NOT EXISTS progress(
            file_hash TEXT, source_file_name TEXT, line_number INTEGER, chinese_part TEXT,
            english_original TEXT, protected_english TEXT, portuguese_translation TEXT,
            status TEXT, error_message TEXT, updated_at TEXT, batch_number INTEGER, attempts INTEGER,
            original_line_ending TEXT, original_line TEXT,
            PRIMARY KEY(file_hash, line_number)
        )""")
        self.conn.commit()

    def upsert_lines(self, file_hash: str, source_file_name: str, lines: Iterable[ParsedLine], batch_number: int = 0) -> None:
        for line in lines:
            self.conn.execute(
                """INSERT INTO progress VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(file_hash,line_number) DO UPDATE SET
                chinese_part=excluded.chinese_part, english_original=excluded.english_original,
                protected_english=excluded.protected_english, portuguese_translation=excluded.portuguese_translation,
                status=excluded.status, error_message=excluded.error_message, updated_at=excluded.updated_at,
                batch_number=excluded.batch_number, attempts=excluded.attempts, original_line_ending=excluded.original_line_ending,
                original_line=excluded.original_line""",
                (file_hash, source_file_name, line.line_number, line.chinese_part, line.english_part,
                 getattr(line, "protected_english", ""), line.portuguese_translation, line.status, line.error_message,
                 __import__('datetime').datetime.utcnow().isoformat(), batch_number, getattr(line, "attempts", 0),
                 line.original_line_ending, line.original_line),
            )
        self.conn.commit()

    def get_lines(self, file_hash: str) -> list[sqlite3.Row]:
        return self.conn.execute("SELECT * FROM progress WHERE file_hash=? ORDER BY line_number", (file_hash,)).fetchall()
