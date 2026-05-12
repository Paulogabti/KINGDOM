from types import SimpleNamespace
from pathlib import Path

import cli
from src.config import Settings
from src.parser import parse_file
from src.providers import TranslationResult
from src.providers.base import ProviderRateLimitError, ProviderPermanentError


def test_combined_batch_respects_char_limit(tmp_path: Path):
    source = tmp_path / 'in.txt'
    source.write_text('中|aaaa\n中|bbbb\n中|cccc\n', encoding='utf-8')
    lines = [l for l in parse_file(source) if l.separator == '|']
    batch, chars = cli._build_combined_batch(lines, 0, max_lines=10, max_chars=8)
    assert len(batch) == 2
    assert chars <= 8


def test_combined_batch_respects_line_limit(tmp_path: Path):
    source = tmp_path / 'in.txt'
    source.write_text('中|a\n中|b\n中|c\n', encoding='utf-8')
    lines = [l for l in parse_file(source) if l.separator == '|']
    batch, _ = cli._build_combined_batch(lines, 0, max_lines=2, max_chars=100)
    assert len(batch) == 2


def test_cli_accepts_new_batching_flags():
    p = cli.argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('translate')
    t.add_argument('--max-chars-per-batch', type=int)
    t.add_argument('--start-chars-per-batch', type=int)
    t.add_argument('--delay-between-batches', type=float)
    args = p.parse_args(['translate', '--max-chars-per-batch', '12000', '--start-chars-per-batch', '8000', '--delay-between-batches', '0.1'])
    assert args.max_chars_per_batch == 12000
    assert args.start_chars_per_batch == 8000
    assert args.delay_between_batches == 0.1
