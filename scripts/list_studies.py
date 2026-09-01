#!/usr/bin/env python3
"""List the studies currently stored (synced) in the configured Orthanc PACS.

Connection defaults come from ORTHANC_HTTP_URL/_USERNAME/_PASSWORD (see
config.py / .env) and can be overridden with the flags below.

Examples:
    uv run python scripts/list_studies.py
    uv run python scripts/list_studies.py --patient smith
    uv run python scripts/list_studies.py --json
    uv run python scripts/list_studies.py --url http://localhost:8042 --username orthanc --password secret
"""
import argparse
import json
import sys

from dicom_connector import config
from dicom_connector.dicom.orthanc_api import OrthancAPI


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="List studies synced in the Orthanc PACS.")
    parser.add_argument(
        "--url", default=config.ORTHANC_HTTP_CONFIG["url"],
        help=f"Orthanc REST API base URL (default: {config.ORTHANC_HTTP_CONFIG['url']})",
    )
    parser.add_argument(
        "--username", default=config.ORTHANC_HTTP_CONFIG["username"],
        help="Orthanc REST API username",
    )
    parser.add_argument(
        "--password", default=config.ORTHANC_HTTP_CONFIG["password"],
        help="Orthanc REST API password",
    )
    parser.add_argument(
        "--patient",
        help="Only show studies whose patient name or ID contains this text (case-insensitive)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Only fetch/display at most this many studies",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Print raw JSON instead of a table",
    )
    return parser.parse_args(argv)


def fetch_studies(api, study_ids):
    studies = []
    for study_id in study_ids:
        details = api.get_study_details(study_id)
        main_tags = details.get("MainDicomTags", {})
        patient_tags = details.get("PatientMainDicomTags", {})
        studies.append({
            "orthanc_id": study_id,
            "patient_name": patient_tags.get("PatientName", ""),
            "patient_id": patient_tags.get("PatientID", ""),
            "study_date": main_tags.get("StudyDate", ""),
            "study_description": main_tags.get("StudyDescription", ""),
            "study_instance_uid": main_tags.get("StudyInstanceUID", ""),
            "series_count": len(details.get("Series", [])),
        })
    return studies


def matches_patient_filter(study, needle):
    if not needle:
        return True
    needle = needle.lower()
    return needle in study["patient_name"].lower() or needle in study["patient_id"].lower()


def print_table(studies):
    if not studies:
        print("No studies found.")
        return

    headers = ["Patient Name", "Patient ID", "Study Date", "Description", "Series", "Study Instance UID"]
    rows = [
        [
            s["patient_name"], s["patient_id"], s["study_date"], s["study_description"],
            str(s["series_count"]), s["study_instance_uid"],
        ]
        for s in studies
    ]
    widths = [max(len(header), *(len(row[i]) for row in rows)) for i, header in enumerate(headers)]

    def format_row(cols):
        return "  ".join(col.ljust(width) for col, width in zip(cols, widths))

    print(format_row(headers))
    print("  ".join("-" * width for width in widths))
    for row in rows:
        print(format_row(row))
    print(f"\n{len(studies)} study(ies) found.")


def main(argv=None):
    args = parse_args(argv)
    api = OrthancAPI(url=args.url, username=args.username, password=args.password)

    try:
        study_ids = api.get_studies()
        if args.limit is not None:
            study_ids = study_ids[:args.limit]
        studies = fetch_studies(api, study_ids)
    except Exception as exc:
        print(f"Failed to query Orthanc at {args.url}: {exc}", file=sys.stderr)
        return 1

    studies = [s for s in studies if matches_patient_filter(s, args.patient)]

    if args.json:
        print(json.dumps(studies, indent=2))
    else:
        print_table(studies)

    return 0


if __name__ == "__main__":
    sys.exit(main())
