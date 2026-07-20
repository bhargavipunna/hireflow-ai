"""Tests for the CLI.

Uses the argparse parser and invokes subcommand functions directly,
avoiding subprocess overhead.
"""

import pytest

from app.cli.main import build_parser


def test_parser_run():
    parser = build_parser()
    args = parser.parse_args(["run"])
    assert args.command == "run"
    assert callable(args.func)


def test_parser_scrape():
    parser = build_parser()
    args = parser.parse_args(["scrape", "--sources", "wellfound,remote"])
    assert args.command == "scrape"
    assert args.sources == "wellfound,remote"


def test_parser_serve_defaults():
    parser = build_parser()
    args = parser.parse_args(["serve"])
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.reload is False


def test_parser_schedule():
    parser = build_parser()
    args = parser.parse_args(["schedule", "--hour", "10", "--minute", "30"])
    assert args.hour == 10
    assert args.minute == 30


def test_parser_stats():
    parser = build_parser()
    args = parser.parse_args(["stats"])
    assert args.command == "stats"


def test_parser_missing_subcommand():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_stats_subcommand_runs():
    """Invoke cmd_stats directly - should exit 0 without raising."""
    from app.cli.main import cmd_stats
    args = build_parser().parse_args(["stats"])
    assert cmd_stats(args) == 0
