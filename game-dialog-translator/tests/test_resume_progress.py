from pathlib import Path

from src.parser import parse_file
from src.progress import ProgressStore


def test_resume_preserves_translated_and_selects_only_pending(tmp_path: Path):
    source = tmp_path / "dialog.txt"
    source.write_text("中|one\n中|two\nsem separador\n", encoding="utf-8")
    progress_dir = tmp_path / ".progress"

    # Inicializa e marca estados distintos no SQLite.
    initial_lines = parse_file(source)
    store = ProgressStore(progress_dir, source)
    store.initialize_progress(initial_lines)

    initial_lines[0].status = "translated"
    initial_lines[0].portuguese_translation = "um"
    initial_lines[1].status = "pending"
    store.save_batch(initial_lines, batch_number=1)

    # Simula execução com --resume: parse novo + apply_existing antes da seleção.
    resumed_lines = parse_file(source)
    store_resume = ProgressStore(progress_dir, source)
    store_resume.apply_existing(resumed_lines)

    translated_existing = sum(1 for l in resumed_lines if l.status == "translated")
    pending_selected = [l.line_number for l in resumed_lines if l.separator == "|" and l.status in {"pending", "error"}]
    skipped = sum(1 for l in resumed_lines if l.status == "skipped_no_separator")

    assert translated_existing == 1
    assert pending_selected == [2]
    assert skipped == 1
