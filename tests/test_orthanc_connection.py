# test_orthanc_connection.py
"""Integration tests against a live PACS/Orthanc (e.g. `docker compose up
db orthanc`). Previously these only printed results and never asserted
anything, so they "passed" even when the connection was completely
broken. Now they assert for real, and skip cleanly - rather than fail -
when nothing is actually listening, so a plain `pytest` run works
whether or not the stack happens to be up.
"""
import socket
from urllib.parse import urlparse

import pytest
import requests

from dicom_connector import config
from dicom_connector.dicom.network import DicomNetwork
from dicom_connector.dicom.orthanc_api import OrthancAPI

pytestmark = pytest.mark.integration


def _tcp_reachable(host, port, timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _http_reachable(url, timeout=1.0):
    try:
        requests.get(url, timeout=timeout)
        return True
    except requests.exceptions.ConnectionError:
        return False


_PACS_REACHABLE = _tcp_reachable(config.PACS_CONFIG['host'], config.PACS_CONFIG['port'])
_orthanc_host = urlparse(config.ORTHANC_HTTP_CONFIG['url']).hostname or "localhost"
_ORTHANC_HTTP_REACHABLE = _http_reachable(config.ORTHANC_HTTP_CONFIG['url'])

skip_if_no_pacs = pytest.mark.skipif(
    not _PACS_REACHABLE,
    reason=f"No PACS reachable at {config.PACS_CONFIG['host']}:{config.PACS_CONFIG['port']} "
           "- run `docker compose up db orthanc` to enable this test",
)
skip_if_no_orthanc_http = pytest.mark.skipif(
    not _ORTHANC_HTTP_REACHABLE,
    reason=f"No Orthanc HTTP API reachable at {config.ORTHANC_HTTP_CONFIG['url']} "
           "- run `docker compose up db orthanc` to enable this test",
)


@skip_if_no_pacs
def test_dicom_echo_against_live_pacs():
    network = DicomNetwork(config.PACS_CONFIG)
    status = network.echo_scu()
    assert status == 0x0000


@skip_if_no_orthanc_http
def test_orthanc_http_api_lists_studies():
    api = OrthancAPI()
    studies = api.get_studies()

    assert isinstance(studies, list)
    if studies:
        details = api.get_study_details(studies[0])
        assert "MainDicomTags" in details
