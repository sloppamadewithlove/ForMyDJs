#!/usr/bin/env python3
"""ForMyDJ command-line interface.

Wraps the same Python engine that powers the desktop app. Exposes URL/file
conversion, source probe, update check, and a server-launch shortcut.

Designed so any AI agent (Claude, Codex, Gemini, etc.) can invoke ForMyDJ as
a plain CLI. Subcommands mirror the GUI affordances:

  formydj url <link> [--format auto|mp3|wav|aiff] [--output DIR]
  formydj file <path> [--format auto|mp3|wav|aiff] [--output DIR]
  formydj probe <link>
  formydj serve [--port 8765] [--no-browser]
  formydj version
  formydj check-update [--force]
"""

import argparse
import json
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

from app import server


VALID_FORMATS = {"mp3", "wav", "aiff"}


def _autopick_url(url: str) -> str:
    """Pick the smartest output format for a URL by probing the source codec.

    Falls back to mp3 on probe failure (defensive: never auto-upgrade to a
    lossless container without confirmation that the source is lossless).
    """
    try:
        probe = server.probe_url(url)
    except Exception:
        return "mp3"
    codec = (probe.get("codec") or "").lower()
    if codec == "mp3":
        return "mp3"
    if codec in {"aiff", "pcm_s16be", "pcm_s24be"}:
        return "aiff"
    if codec == "wav" or codec.startswith("pcm_"):
        return "wav"
    if codec in {"flac", "alac", "ape", "tta", "wv"}:
        return "aiff"
    return "mp3"


def _autopick_file(path: Path) -> str:
    ext = path.suffix.lstrip(".").lower()
    if ext == "mp3":
        return "mp3"
    if ext in {"wav", "wave"}:
        return "wav"
    if ext in {"aiff", "aif", "aifc"}:
        return "aiff"
    if ext in {"flac", "alac", "m4a", "ape", "tta", "wv"}:
        return "aiff"
    return "mp3"


def _resolve_format(requested: str, *, kind: str, value) -> str:
    fmt = (requested or "auto").lower()
    if fmt == "auto":
        return _autopick_url(value) if kind == "url" else _autopick_file(Path(value))
    if fmt not in VALID_FORMATS:
        raise SystemExit(f"format must be one of: auto, {', '.join(sorted(VALID_FORMATS))}")
    return fmt


def _run_job_sync(input_kind: str, input_value: str, output_format: str, output_dir: Path) -> dict:
    """Submit a job and execute process_job synchronously in-thread.

    The desktop server enqueues onto a ThreadPoolExecutor for concurrency;
    the CLI just inlines the work so stdout reflects real-time progress.
    """
    job_id = uuid.uuid4().hex
    output_dir.mkdir(parents=True, exist_ok=True)
    with server.jobs_lock:
        server.jobs[job_id] = {
            "id": job_id,
            "created_at": time.time(),
            "created_at_display": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": time.time(),
            "input_kind": input_kind,
            "input_value": input_value,
            "format": output_format,
            "output_dir": str(output_dir),
            "status": "queued",
            "progress": "Waiting",
            "warnings": [],
        }
    server.process_job(job_id)
    with server.jobs_lock:
        return dict(server.jobs[job_id])


def _print_result(job: dict, *, json_output: bool) -> int:
    if json_output:
        print(json.dumps(job, indent=2, default=str))
    if job.get("status") == "finished":
        if not json_output:
            print(f"Saved: {job.get('output_path')}")
            for warning in job.get("warnings", []) or []:
                print(f"  ! {warning}")
        return 0
    if not json_output:
        print(f"Failed: {job.get('error') or job.get('progress') or 'unknown error'}", file=sys.stderr)
    return 1


def _cmd_url(args: argparse.Namespace) -> int:
    output_dir = Path(args.output).expanduser() if args.output else Path.cwd()
    output_format = _resolve_format(args.format, kind="url", value=args.url)
    job = _run_job_sync("url", args.url, output_format, output_dir)
    return _print_result(job, json_output=args.json)


def _cmd_file(args: argparse.Namespace) -> int:
    source = Path(args.path).expanduser().resolve()
    if not source.exists():
        print(f"File not found: {source}", file=sys.stderr)
        return 1
    output_dir = Path(args.output).expanduser() if args.output else Path.cwd()
    output_format = _resolve_format(args.format, kind="file", value=source)
    job = _run_job_sync("file", str(source), output_format, output_dir)
    return _print_result(job, json_output=args.json)


def _cmd_probe(args: argparse.Namespace) -> int:
    try:
        result = server.probe_url(args.url)
    except Exception as exc:
        print(f"Probe failed: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"Title:    {result.get('title') or '(unknown)'}")
        print(f"Artist:   {result.get('artist') or '(unknown)'}")
        print(f"Codec:    {result.get('codec') or '(unknown)'}")
        print(f"Lossy:    {'yes' if result.get('lossy') else 'no'}")
        print(f"Duration: {result.get('duration')}s")
        print(f"Suggested format: {_autopick_url(args.url)}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    import os
    if args.port:
        os.environ["FORMYDJ_PORT"] = str(args.port)
    if args.no_browser:
        os.environ["FORMYDJ_NO_BROWSER"] = "1"
    server.main()
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    print(server.VERSION)
    return 0


def _cmd_check_update(args: argparse.Namespace) -> int:
    payload = server.check_for_update(force=args.force)
    if args.json:
        print(json.dumps(payload, indent=2, default=str))
        return 0
    print(f"Current: v{payload['current']}")
    if payload.get("error"):
        print(f"Check failed: {payload['error']}", file=sys.stderr)
        return 1
    latest = payload.get("latest")
    if not latest:
        print("Could not determine latest version.", file=sys.stderr)
        return 1
    print(f"Latest:  v{latest}")
    if payload.get("update_available"):
        print(f"Update available: {payload.get('html_url') or 'check GitHub releases'}")
    else:
        print("Up to date.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="formydj",
        description="Local audio downloader/converter for DJs. Source-matching, bit-exact passthrough.",
    )
    parser.add_argument("--version", action="version", version=f"formydj {server.VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)

    p_url = sub.add_parser("url", help="Download and convert a SoundCloud/YouTube link")
    p_url.add_argument("url", help="Source URL")
    p_url.add_argument("--format", default="auto", help="auto (match source) | mp3 | wav | aiff")
    p_url.add_argument("--output", default=None, help="Output directory (default: current working directory)")
    p_url.add_argument("--json", action="store_true", help="Emit JSON result")
    p_url.set_defaults(func=_cmd_url)

    p_file = sub.add_parser("file", help="Convert a local audio file")
    p_file.add_argument("path", help="Path to source audio file")
    p_file.add_argument("--format", default="auto", help="auto (match source) | mp3 | wav | aiff")
    p_file.add_argument("--output", default=None, help="Output directory (default: current working directory)")
    p_file.add_argument("--json", action="store_true", help="Emit JSON result")
    p_file.set_defaults(func=_cmd_file)

    p_probe = sub.add_parser("probe", help="Inspect a URL without downloading")
    p_probe.add_argument("url", help="Source URL")
    p_probe.add_argument("--json", action="store_true", help="Emit JSON result")
    p_probe.set_defaults(func=_cmd_probe)

    p_serve = sub.add_parser("serve", help="Launch the local web UI at 127.0.0.1:PORT")
    p_serve.add_argument("--port", type=int, default=None, help="Port (default: 8765)")
    p_serve.add_argument("--no-browser", action="store_true", help="Do not auto-open the browser")
    p_serve.set_defaults(func=_cmd_serve)

    p_ver = sub.add_parser("version", help="Print the installed ForMyDJ version")
    p_ver.set_defaults(func=_cmd_version)

    p_upd = sub.add_parser("check-update", help="Check GitHub for a newer release")
    p_upd.add_argument("--force", action="store_true", help="Skip the 6-hour cache")
    p_upd.add_argument("--json", action="store_true", help="Emit JSON result")
    p_upd.set_defaults(func=_cmd_check_update)

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
