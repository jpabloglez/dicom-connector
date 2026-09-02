# test_studies.py
from dicom_connector.dicom.studies import fetch_studies, matches_patient_filter


class FakeOrthancAPI:
    def __init__(self, studies_by_id):
        self._studies_by_id = studies_by_id

    def get_studies(self):
        return list(self._studies_by_id.keys())

    def get_study_details(self, study_id):
        return self._studies_by_id[study_id]


def make_details(patient_name, patient_id, study_date="20240101",
                  description="Chest", uid="1.2.3", series=("s1", "s2")):
    return {
        "MainDicomTags": {
            "StudyDate": study_date, "StudyDescription": description, "StudyInstanceUID": uid,
        },
        "PatientMainDicomTags": {"PatientName": patient_name, "PatientID": patient_id},
        "Series": list(series),
    }


def test_fetch_studies_summarizes_every_study_when_no_ids_given():
    api = FakeOrthancAPI({
        "id-1": make_details("Doe^John", "P1", uid="1.1"),
        "id-2": make_details("Smith^Jane", "P2", uid="1.2", series=("s1",)),
    })

    studies = fetch_studies(api)

    assert len(studies) == 2
    assert studies[0] == {
        "orthanc_id": "id-1", "patient_name": "Doe^John", "patient_id": "P1",
        "study_date": "20240101", "study_description": "Chest",
        "study_instance_uid": "1.1", "series_count": 2,
    }
    assert studies[1]["series_count"] == 1


def test_fetch_studies_respects_explicit_study_ids():
    api = FakeOrthancAPI({
        "id-1": make_details("Doe^John", "P1"),
        "id-2": make_details("Smith^Jane", "P2"),
    })

    studies = fetch_studies(api, study_ids=["id-2"])

    assert len(studies) == 1
    assert studies[0]["patient_name"] == "Smith^Jane"


def test_fetch_studies_defaults_missing_tags_to_empty_string():
    api = FakeOrthancAPI({"id-1": {"MainDicomTags": {}, "PatientMainDicomTags": {}}})

    studies = fetch_studies(api)

    assert studies[0]["patient_name"] == ""
    assert studies[0]["study_instance_uid"] == ""
    assert studies[0]["series_count"] == 0


def test_matches_patient_filter_matches_name_or_id_case_insensitively():
    study = {"patient_name": "Doe^John", "patient_id": "P1"}

    assert matches_patient_filter(study, "doe")
    assert matches_patient_filter(study, "P1")
    assert matches_patient_filter(study, "p1")
    assert not matches_patient_filter(study, "smith")


def test_matches_patient_filter_empty_needle_matches_everything():
    study = {"patient_name": "Doe^John", "patient_id": "P1"}

    assert matches_patient_filter(study, "")
    assert matches_patient_filter(study, None)
