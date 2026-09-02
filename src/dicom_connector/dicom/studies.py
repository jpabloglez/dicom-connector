# dicom/studies.py
"""Shared logic for summarizing/filtering Orthanc studies, used by both
scripts/list_studies.py and the in-app PACS browser (ui/pacs_browser.py).
"""


def fetch_studies(api, study_ids=None):
    """Summarize each study_id (or every study on the PACS if None) via
    OrthancAPI.get_study_details()."""
    if study_ids is None:
        study_ids = api.get_studies()

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
    """True if `needle` (case-insensitive) is contained in the study's
    patient name or patient ID. An empty/falsy needle matches everything."""
    if not needle:
        return True
    needle = needle.lower()
    return needle in study["patient_name"].lower() or needle in study["patient_id"].lower()
