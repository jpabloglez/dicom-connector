# test_orthanc_api.py
"""Unit tests for OrthancAPI against a mocked `requests` - no live Orthanc
needed. See test_orthanc_connection.py for the live-service integration
test of this same class.
"""
from unittest.mock import MagicMock, patch

import pytest

from dicom_connector.dicom.orthanc_api import OrthancAPI


def make_response(status_code=200, json_value=None):
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_value
    return response


@pytest.fixture
def api():
    return OrthancAPI(url="http://orthanc.example", username="user", password="pass")


def test_constructor_overrides_take_precedence_over_config():
    api = OrthancAPI(url="http://custom:9999", username="u", password="p")
    assert api.base_url == "http://custom:9999"
    assert api.auth.username == "u"
    assert api.auth.password == "p"


def test_constructor_falls_back_to_config_when_no_overrides():
    api = OrthancAPI()
    from dicom_connector import config
    assert api.base_url == config.ORTHANC_HTTP_CONFIG["url"]


def test_get_studies_returns_json_on_success(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.get",
               return_value=make_response(200, ["id-1", "id-2"])) as get:
        result = api.get_studies()

    assert result == ["id-1", "id-2"]
    get.assert_called_once_with("http://orthanc.example/studies", auth=api.auth)


def test_get_studies_raises_on_non_200(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.get", return_value=make_response(401)), \
         pytest.raises(Exception, match="401"):
        api.get_studies()


def test_get_study_details_hits_correct_url(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.get",
               return_value=make_response(200, {"ID": "id-1"})) as get:
        result = api.get_study_details("id-1")

    assert result == {"ID": "id-1"}
    get.assert_called_once_with("http://orthanc.example/studies/id-1", auth=api.auth)


def test_get_study_details_raises_on_non_200(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.get", return_value=make_response(404)), \
         pytest.raises(Exception, match="404"):
        api.get_study_details("missing-id")


def test_delete_study_returns_true_on_success(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.delete",
               return_value=make_response(200)) as delete:
        result = api.delete_study("id-1")

    assert result is True
    delete.assert_called_once_with("http://orthanc.example/studies/id-1", auth=api.auth)


def test_delete_study_raises_on_non_200(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.delete", return_value=make_response(403)), \
         pytest.raises(Exception, match="403"):
        api.delete_study("id-1")


def test_get_instance_tags_returns_json_on_success(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.get",
               return_value=make_response(200, {"0010,0010": {"Value": "Doe^John"}})) as get:
        result = api.get_instance_tags("inst-1")

    assert result == {"0010,0010": {"Value": "Doe^John"}}
    get.assert_called_once_with("http://orthanc.example/instances/inst-1/tags", auth=api.auth)


def test_get_instance_tags_raises_on_non_200(api):
    with patch("dicom_connector.dicom.orthanc_api.requests.get", return_value=make_response(500)), \
         pytest.raises(Exception, match="500"):
        api.get_instance_tags("inst-1")
