# test_orthanc_connection.py
from dicom_connector import config
from dicom_connector.dicom.network import DicomNetwork
from dicom_connector.dicom.orthanc_api import OrthancAPI


def test_dicom_echo():
    network = DicomNetwork(config.PACS_CONFIG)
    try:
        status = network.echo_scu()
        print(f"DICOM Echo Status: {status}")
    except Exception as e:
        print(f"DICOM Echo failed: {str(e)}")


def test_orthanc_http_api():
    api = OrthancAPI()
    try:
        studies = api.get_studies()
        print(f"Number of studies in Orthanc: {len(studies)}")
    except Exception as e:
        print(f"Failed to get studies from Orthanc: {str(e)}")


if __name__ == "__main__":
    print("Testing DICOM Echo with Orthanc...")
    test_dicom_echo()

    print("\nTesting Orthanc HTTP API...")
    test_orthanc_http_api()
