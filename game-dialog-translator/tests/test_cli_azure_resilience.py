from types import SimpleNamespace
from pathlib import Path

import cli
from src.providers.base import ProviderRateLimitError


def _args(tmp_path: Path, debug: bool = False):
    source = tmp_path / 'in.txt'
    source.write_text('中|a\n中|b\n', encoding='utf-8')
    return SimpleNamespace(
        input=str(source), output_dir=str(tmp_path / 'out'), batch_size=2, deepl_plan='free', deepl_api_url=None,
        source_lang='EN', target_lang='PT-BR', formality='prefer_more', resume=False, overwrite=False,
        retry_errors=False, provider='azure', no_fallback=True, azure_key='k', azure_endpoint='https://x',
        azure_region='r', auto_export=False, debug=debug
    )


def test_rate_limit_error_has_retry_after():
    err = ProviderRateLimitError('x', retry_after=10)
    assert err.retry_after == 10


def test_friendly_error_without_traceback():
    msg = cli._friendly_provider_error(ProviderRateLimitError('429'))
    assert 'Rate limit' in msg


def test_debug_flag_available():
    p = cli.argparse.ArgumentParser()
    sub = p.add_subparsers(dest='cmd', required=True)
    t = sub.add_parser('translate')
    t.add_argument('--debug', action='store_true')
    args = p.parse_args(['translate', '--debug'])
    assert args.debug is True
