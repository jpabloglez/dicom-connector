#!/usr/bin/env python3
"""Anonymize local DICOM files before sending them elsewhere.

Reuses one Anonymizer across every file passed in a single run, so files
sharing a StudyInstanceUID/PatientID/etc. before anonymization keep
mapping to the same new identifiers afterward (see DatasetAnonymizer).

Examples:
    uv run python scripts/anonymize.py study/*.dcm --output anonymized/
    uv run python scripts/anonymize.py study/ --output anonymized/ --seed demo
"""
import argparse
import sys
from pathlib import Path

from rich.console import Console

from dicom_connector.dicom.anonymizer import DatasetAnonymizer
from dicom_connector.dicom.file_handler import DicomFileHandler

console = Console()
error_console = Console(stderr=True)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Anonymize local DICOM files before sending them elsewhere.")
    parser.add_argument(
        "input", nargs="+",
        help="DICOM file(s) or director(ies) (directories are searched recursively for *.dcm)",
    )
    parser.add_argument(
        "--output", "-o", required=True,
        help="Directory to write anonymized copies into (created if missing)",
    )
    parser.add_argument(
        "--seed",
        help="Seed the anonymizer for reproducible output across separate runs",
    )
    return parser.parse_args(argv)


def collect_files(inputs):
    files = []
    for raw in inputs:
        path = Path(raw)
        if path.is_dir():
            files.extend(sorted(path.rglob("*.dcm")))
        elif path.is_file():
            files.append(path)
        else:
            error_console.print(f"[yellow]Skipping (not found): {path}[/yellow]")
    return files


def main(argv=None):
    args = parse_args(argv)
    files = collect_files(args.input)
    if not files:
        error_console.print("[bold red]No .dcm files found.[/bold red]")
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    file_handler = DicomFileHandler()
    anonymizer = DatasetAnonymizer(seed=args.seed)

    succeeded = 0
    for path in files:
        try:
            dataset = file_handler.read_dicom_file(path)
            anonymized = anonymizer.anonymize(dataset)
            out_path = output_dir / path.name
            file_handler.write_dicom_file(anonymized, out_path)
        except Exception as exc:
            error_console.print(f"[red]Failed: {path}: {exc}[/red]")
            continue
        console.print(f"[green]OK[/green]  {path} -> {out_path}")
        succeeded += 1

    console.print(f"\n[bold]{succeeded}/{len(files)}[/bold] file(s) anonymized into {output_dir}")
    return 0 if succeeded == len(files) else 1


if __name__ == "__main__":
    sys.exit(main())
