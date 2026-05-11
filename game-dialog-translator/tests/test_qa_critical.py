from pathlib import Path

from src.exporter import export_from_progress
from src.parser import ParsedLine
from src.progress import ProgressStore
from src.translator import DeepLTranslationSettings, translate_batch_with_deepl
from src.validator import validate_lines


def test_progress_store_creates_sqlite_by_hash(tmp_path: Path):
    source = tmp_path / "in.txt"
    source.write_text("中|A\n", encoding="utf-8")
    store = ProgressStore(tmp_path / ".progress", source)
    assert store.db_path.name == f"{store.file_hash}.sqlite"
    assert store.db_path.exists()


def test_resume_does_not_retranslate_translated(tmp_path: Path):
    source = tmp_path / "in.txt"
    source.write_text("中|A\n文|B\n", encoding="utf-8")
    store = ProgressStore(tmp_path / ".progress", source)
    lines = [
        ParsedLine(line_number=1, chinese_part="中", separator="|", english_part="A", status="translated", portuguese_translation="AA"),
        ParsedLine(line_number=2, chinese_part="文", separator="|", english_part="B", status="pending"),
    ]
    store.save_batch(lines)
    loaded = __import__("src.parser", fromlist=["parse_file"]).parse_file(source)
    store.apply_existing(loaded)
    translatable = [l for l in loaded if l.separator == "|" and l.status in {"pending", "error"}]
    assert [x.line_number for x in translatable] == [2]


def test_retry_errors_selects_only_error(tmp_path: Path):
    source = tmp_path / "in.txt"
    source.write_text("中|A\n文|B\n", encoding="utf-8")
    store = ProgressStore(tmp_path / ".progress", source)
    store.save_batch([
        ParsedLine(line_number=1, chinese_part="中", separator="|", english_part="A", status="error", error_message="x"),
        ParsedLine(line_number=2, chinese_part="文", separator="|", english_part="B", status="translated", portuguese_translation="BB"),
    ])
    store.mark_errors_for_retry()
    rows = {r["line_number"]: r for r in store.load_progress()}
    assert rows[1]["status"] == "pending"
    assert rows[2]["status"] == "translated"


def test_exporter_blocks_pending_error_without_force(tmp_path: Path):
    source = tmp_path / "in.txt"
    source.write_text("中|A\n", encoding="utf-8")
    store = ProgressStore(tmp_path / ".progress", source)
    store.save_batch([ParsedLine(line_number=1, chinese_part="中", separator="|", english_part="A", status="error")])
    try:
        export_from_progress(source, tmp_path, store, block_on_pending_error=True)
        assert False
    except ValueError:
        assert True


def test_exporter_allows_force_and_sets_report_flag(tmp_path: Path):
    source = tmp_path / "in.txt"
    source.write_text("中|A\n", encoding="utf-8")
    store = ProgressStore(tmp_path / ".progress", source)
    store.save_batch([ParsedLine(line_number=1, chinese_part="中", separator="|", english_part="A", status="error")])
    out, report, _ = export_from_progress(source, tmp_path, store, force_export=True, block_on_pending_error=True)
    assert out is not None and out.exists()
    assert '"force_export": true' in report.read_text(encoding="utf-8")


def test_validator_fails_if_original_placeholder_missing():
    o = [ParsedLine(line_number=1, chinese_part="中", separator="|", english_part="Hi {player}")]
    t = [ParsedLine(line_number=1, chinese_part="中", separator="|", english_part="Oi")]
    res = validate_lines(o, t)
    assert not res.passed
    assert any(e.code == "PLACEHOLDER_MISSING" for e in res.errors)


def test_translator_mock_does_not_send_chinese_and_preserves_order(monkeypatch):
    import src.translator as tr

    captured = {}

    class FakeResp:
        def __init__(self, text):
            self.text = text

    class FakeTranslator:
        def __init__(self, *a, **k):
            pass

        def translate_text(self, texts, **kwargs):
            captured["texts"] = texts
            return [FakeResp("B"), FakeResp("A")]

    monkeypatch.setattr(tr.deepl, "Translator", FakeTranslator)
    items = [{"line_number": 2, "text": "EN2"}, {"line_number": 1, "text": "EN1"}]
    out = translate_batch_with_deepl(items, DeepLTranslationSettings(api_key="k", api_url="https://api-free.deepl.com"))
    assert captured["texts"] == ["EN2", "EN1"]
    assert [x["line_number"] for x in out] == [2, 1]
