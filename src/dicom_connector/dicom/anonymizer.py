# dicom/anonymizer.py
"""De-identify a dataset before sending it to a PACS.

Wraps dicognito (https://github.com/dicognito/dicognito), which implements
the DICOM PS3.15 Basic Application Level Confidentiality Profile: patient/
study identifiers, dates/times (shifted consistently, not blanked), all
UIDs, and a long list of other identifying elements. Clinical content
(Modality, PixelData, etc.) is left untouched.
"""
import copy

from dicognito.anonymizer import Anonymizer


class DatasetAnonymizer:
    """Wraps a single dicognito.Anonymizer instance.

    Reuse one instance across every file anonymized in a session (rather
    than constructing a new one per file) so datasets that share a
    StudyInstanceUID/PatientID/etc. before anonymization keep mapping to
    the *same* new identifiers afterward - dicognito's consistent-mapping
    guarantee only holds within one Anonymizer instance, not across them.
    """

    def __init__(self, seed=None):
        self._anonymizer = Anonymizer(seed=seed)

    def anonymize(self, dataset):
        """Return a de-identified copy of `dataset`; the original is untouched.

        `dataset.file_meta` must be present (as it always is for a dataset
        read via DicomFileHandler.read_dicom_file / pydicom.dcmread) -
        dicognito anonymizes file-meta UIDs too.
        """
        if getattr(dataset, "file_meta", None) is None:
            raise ValueError(
                "Cannot anonymize a dataset with no file_meta - "
                "read it with DicomFileHandler.read_dicom_file() first."
            )

        anonymized = copy.deepcopy(dataset)
        self._anonymizer.anonymize(anonymized)
        return anonymized
