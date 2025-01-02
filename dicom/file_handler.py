# dicom/file_handler.py
import pydicom

class DicomFileHandler:
    def __init__(self):
        pass

    def read_dicom_file(self, file_path):
        try:
            return pydicom.dcmread(file_path)
        except Exception as e:
            raise Exception(f"Error reading DICOM file: {str(e)}")

    def write_dicom_file(self, dataset, file_path):
        try:
            dataset.save_as(file_path)
        except Exception as e:
            raise Exception(f"Error writing DICOM file: {str(e)}")

    def get_dicom_metadata(self, dataset):
        metadata = {
            "PatientName": str(dataset.PatientName) if 'PatientName' in dataset else "N/A",
            "StudyDate": str(dataset.StudyDate) if 'StudyDate' in dataset else "N/A",
            "Modality": str(dataset.Modality) if 'Modality' in dataset else "N/A",
            "StudyDescription": str(dataset.StudyDescription) if 'StudyDescription' in dataset else "N/A"
        }
        return metadata