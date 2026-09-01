# test_anonymizer.py
import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dicom_connector.dicom.anonymizer import DatasetAnonymizer


def make_dataset(patient_name="Doe^John", patient_id="P1", study_uid=None):
    ds = Dataset()
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = "19800101"
    ds.Modality = "CT"
    ds.StudyDate = "20240101"
    ds.StudyInstanceUID = study_uid or generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.SOPInstanceUID = generate_uid()
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    ds.PixelData = b"\x01\x02\x03\x04"
    ds.is_little_endian = True
    ds.is_implicit_VR = False

    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta = file_meta
    return ds


def test_anonymize_returns_a_copy_original_untouched():
    original = make_dataset()
    original_name = str(original.PatientName)

    result = DatasetAnonymizer().anonymize(original)

    assert str(original.PatientName) == original_name
    assert str(result.PatientName) != original_name


def test_anonymize_changes_identifying_fields():
    ds = make_dataset(patient_name="Doe^John", patient_id="P1")

    result = DatasetAnonymizer().anonymize(ds)

    assert str(result.PatientName) != "Doe^John"
    assert result.PatientID != "P1"
    assert result.PatientBirthDate != "19800101"
    assert result.StudyInstanceUID != ds.StudyInstanceUID


def test_anonymize_preserves_clinical_content():
    ds = make_dataset()
    ds.PixelData = b"\x11\x22\x33\x44"

    result = DatasetAnonymizer().anonymize(ds)

    assert result.Modality == "CT"
    assert result.PixelData == b"\x11\x22\x33\x44"


def test_same_anonymizer_maps_shared_identifiers_consistently():
    shared_study_uid = generate_uid()
    ds1 = make_dataset(patient_id="P1", study_uid=shared_study_uid)
    ds2 = make_dataset(patient_id="P1", study_uid=shared_study_uid)

    anonymizer = DatasetAnonymizer()  # reused across both, as intended
    result1 = anonymizer.anonymize(ds1)
    result2 = anonymizer.anonymize(ds2)

    assert result1.StudyInstanceUID == result2.StudyInstanceUID
    assert str(result1.PatientID) == str(result2.PatientID)


def test_different_anonymizer_instances_map_differently():
    shared_study_uid = generate_uid()
    ds1 = make_dataset(study_uid=shared_study_uid)
    ds2 = make_dataset(study_uid=shared_study_uid)

    result1 = DatasetAnonymizer().anonymize(ds1)
    result2 = DatasetAnonymizer().anonymize(ds2)

    assert result1.StudyInstanceUID != result2.StudyInstanceUID


def test_missing_file_meta_raises_a_clear_error():
    ds = Dataset()
    ds.PatientName = "Doe^John"

    with pytest.raises(ValueError, match="file_meta"):
        DatasetAnonymizer().anonymize(ds)
