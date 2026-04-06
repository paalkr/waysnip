"""CLI entry point — parse arguments and dispatch to the application."""

from __future__ import annotations

import argparse
import os
import subprocess

from waysnip.constants import APP_DISPLAY_NAME, APP_VERSION, CONFIG_FILE


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="waysnip",
        description=f"{APP_DISPLAY_NAME} — lightweight Wayland screenshot & annotation tool",
    )
    parser.add_argument(
        "--version", action="version", version=f"{APP_DISPLAY_NAME} {APP_VERSION}"
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("region", help="Region capture (default)")
    sub.add_parser("window", help="Window capture (portal interactive mode)")
    sub.add_parser("fullscreen", help="Fullscreen capture")
    sub.add_parser("gallery", help="Open the screenshot gallery")

    config_parser = sub.add_parser("config", help="Open settings GUI")
    config_parser.add_argument(
        "--edit",
        action="store_true",
        help="Open the config TOML in $EDITOR instead of the GUI",
    )

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    command = args.command or "region"

    # `config --edit` is a special case — just open the file in $EDITOR.
    if command == "config" and getattr(args, "edit", False):
        editor = os.environ.get("EDITOR", "xdg-open")
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not CONFIG_FILE.exists():
            # Ensure the file exists so the editor doesn't complain.
            from waysnip.config import AppConfig

            AppConfig().save_to_disk()
        subprocess.run([editor, str(CONFIG_FILE)])
        return

    # Hand off to the application layer (handles single-instance IPC).
    from waysnip.app import run

    run(command)
