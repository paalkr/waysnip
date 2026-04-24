"""Tests for waysnip CLI argument parsing."""

from __future__ import annotations

import pytest

# cli.py may not be in this worktree — try to import
try:
    from waysnip.cli import build_parser

    HAS_CLI = True
except ImportError:
    HAS_CLI = False

pytestmark = pytest.mark.skipif(
    not HAS_CLI, reason="waysnip.cli not available in this worktree"
)


class TestDefaultCommand:
    def test_no_args_gives_none_command(self):
        """With no arguments, parser.command is None (main() defaults to 'region')."""
        parser = build_parser()
        args = parser.parse_args([])
        assert args.command is None


class TestSubcommands:
    @pytest.mark.parametrize(
        "subcmd",
        ["region", "fullscreen", "gallery", "config"],
    )
    def test_subcommand_recognized(self, subcmd):
        parser = build_parser()
        args = parser.parse_args([subcmd])
        assert args.command == subcmd


class TestConfigEdit:
    def test_config_edit_flag(self):
        parser = build_parser()
        args = parser.parse_args(["config", "--edit"])
        assert args.command == "config"
        assert args.edit is True

    def test_config_without_edit(self):
        parser = build_parser()
        args = parser.parse_args(["config"])
        assert args.command == "config"
        assert args.edit is False


class TestVersionFlag:
    def test_version_exits(self):
        parser = build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["--version"])
        assert exc_info.value.code == 0
