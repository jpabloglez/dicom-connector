# test_network.py
"""Two layers of coverage for DicomNetwork:

- association-level methods (echo_scu, send_to_pacs, query_pacs,
  receive_from_pacs) mocked at DicomNetwork._build_ae, since a real
  association needs a real PACS on the other end
- handle_store()/start_store_scp() exercised for real against a local
  Storage SCP on an ephemeral port and a real C-STORE - hermetic (no
  Docker/external services, loopback only), and the strongest evidence
  that persistence actually works, matching the manual verification done
  when this feature was first built
"""
import shutil
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid
from pynetdicom import AE, evt
from pynetdicom.sop_class import CTImageStorage

from dicom_connector.dicom.network import DicomNetwork

PACS_CONFIG = {
    "host": "pacs.example", "port": 4242, "ae_title": "REMOTE",
    "calling_ae_title": "MYAETITLE",
}


def make_mock_association(is_established=True):
    assoc = MagicMock()
    assoc.is_established = is_established
    return assoc


@pytest.fixture
def net():
    return DicomNetwork(PACS_CONFIG)


@pytest.fixture
def mock_ae(net):
    """Patch DicomNetwork._build_ae to return a controllable mock AE, and
    return (ae, assoc) so tests can configure send_c_*/associate."""
    ae = MagicMock()
    assoc = make_mock_association()
    ae.associate.return_value = assoc
    with patch.object(net, "_build_ae", return_value=ae):
        yield ae, assoc


def test_build_ae_uses_configured_calling_ae_title():
    net = DicomNetwork(PACS_CONFIG)
    ae = net._build_ae()
    assert ae.ae_title == "MYAETITLE"


def test_associate_raises_when_not_established(net):
    ae = MagicMock()
    ae.associate.return_value = make_mock_association(is_established=False)

    with pytest.raises(Exception, match="Association rejected"):
        net._associate(ae)


def test_associate_calls_with_configured_host_and_port(net):
    ae = MagicMock()
    ae.associate.return_value = make_mock_association(is_established=True)

    net._associate(ae)

    ae.associate.assert_called_once_with("pacs.example", 4242, ae_title="REMOTE")


def test_echo_scu_returns_status_on_success(net, mock_ae):
    _ae, assoc = mock_ae
    assoc.send_c_echo.return_value = MagicMock(Status=0x0000)

    result = net.echo_scu()

    assert result == 0x0000
    assoc.release.assert_called_once()


def test_echo_scu_raises_when_no_response(net, mock_ae):
    _ae, assoc = mock_ae
    assoc.send_c_echo.return_value = None

    with pytest.raises(Exception, match="C-ECHO request failed"):
        net.echo_scu()


def test_echo_scu_releases_association_even_on_failure(net, mock_ae):
    _ae, assoc = mock_ae
    assoc.send_c_echo.return_value = None

    with pytest.raises(Exception, match="C-ECHO"):
        net.echo_scu()

    assoc.release.assert_called_once()


def test_send_to_pacs_requests_verification_and_sop_class_contexts(net, mock_ae):
    ae, assoc = mock_ae
    assoc.send_c_store.return_value = MagicMock(Status=0x0000)
    dataset = Dataset()
    dataset.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"

    result = net.send_to_pacs(dataset)

    requested = [call.args[0] for call in ae.add_requested_context.call_args_list]
    assert "1.2.840.10008.1.1" in [str(r) for r in requested]  # Verification
    assert dataset.SOPClassUID in requested
    assoc.send_c_store.assert_called_once_with(dataset)
    assert result.Status == 0x0000
    assoc.release.assert_called_once()


def test_query_pacs_keeps_only_valid_responses(net, mock_ae):
    _ae, assoc = mock_ae
    good_identifier = Dataset()
    good_identifier.PatientName = "Doe^John"
    assoc.send_c_find.return_value = [
        (MagicMock(), good_identifier),  # valid
        (None, good_identifier),         # falsy status - excluded
        (MagicMock(), None),             # no identifier - excluded
    ]

    results = net.query_pacs(Dataset())

    assert results == [good_identifier]


def test_receive_from_pacs_builds_correct_move_identifier(net, mock_ae):
    _ae, assoc = mock_ae
    assoc.send_c_move.return_value = []
    study_uid = generate_uid()

    net.receive_from_pacs(study_uid)

    (identifier, move_aet, query_model), _kwargs = assoc.send_c_move.call_args
    assert identifier.QueryRetrieveLevel == "STUDY"
    assert identifier.StudyInstanceUID == study_uid
    assert move_aet == "MYAETITLE"
    assert str(query_model) == "1.2.840.10008.5.1.4.1.2.2.2"  # StudyRoot Move


def test_receive_from_pacs_releases_association(net, mock_ae):
    _ae, assoc = mock_ae
    assoc.send_c_move.return_value = []

    net.receive_from_pacs(generate_uid())

    assoc.release.assert_called_once()


# --- real local Storage SCP, not mocked ---

def _make_ct_instance():
    ds = Dataset()
    ds.SOPClassUID = CTImageStorage
    ds.SOPInstanceUID = generate_uid()
    ds.PatientName = "Test^Patient"
    ds.Modality = "CT"
    ds.StudyInstanceUID = generate_uid()
    ds.SeriesInstanceUID = generate_uid()
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta = file_meta
    return ds


def test_storage_scp_persists_received_instance_via_real_c_store():
    storage_dir = Path(tempfile.mkdtemp())
    try:
        net = DicomNetwork(PACS_CONFIG, storage_dir=storage_dir)

        scp_ae = net._build_ae()
        scp_ae.add_supported_context(CTImageStorage)
        server = scp_ae.start_server(
            ("", 0), block=False, evt_handlers=[(evt.EVT_C_STORE, net.handle_store)],
        )
        port = server.server_address[1]
        time.sleep(0.2)

        instance = _make_ct_instance()
        client_ae = AE(ae_title="SENDER")
        client_ae.add_requested_context(CTImageStorage)
        assoc = client_ae.associate("localhost", port, ae_title="MYAETITLE")
        assert assoc.is_established
        status = assoc.send_c_store(instance)
        assoc.release()

        assert status.Status == 0x0000

        written = storage_dir / f"{instance.SOPInstanceUID}.dcm"
        assert written.exists()

        import pydicom
        read_back = pydicom.dcmread(written)
        assert read_back.SOPInstanceUID == instance.SOPInstanceUID
        assert read_back.PatientName == instance.PatientName

        server.shutdown()
    finally:
        shutil.rmtree(storage_dir, ignore_errors=True)
