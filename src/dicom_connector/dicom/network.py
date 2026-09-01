# dicom/network.py
"""
This DicomNetwork class provides methods for sending DICOM
files to PACS, querying PACS, and receiving files from PACS.
It also includes a basic implementation of a Storage SCP
server to receive DICOM files.
"""
import logging
from pathlib import Path

from pydicom.dataset import Dataset
from pynetdicom import AE, AllStoragePresentationContexts, evt
from pynetdicom.sop_class import (
    PatientRootQueryRetrieveInformationModelFind,
    StudyRootQueryRetrieveInformationModelMove,
    Verification,
)

logger = logging.getLogger(__name__)


class DicomNetwork:
    def __init__(self, pacs_config, storage_dir="received_dicom"):
        self.pacs_config = pacs_config
        self.calling_ae_title = pacs_config.get('calling_ae_title', 'MYAETITLE')
        self.storage_dir = Path(storage_dir)

    def _build_ae(self):
        """Build a fresh AE for one association.

        A single long-lived AE would accumulate requested contexts across
        calls (each add_requested_context() call adds another entry, and an
        association is capped at 128 presentation contexts), so every
        operation below gets its own AE instead of reusing self.ae.
        """
        return AE(ae_title=self.calling_ae_title)

    def _associate(self, ae):
        assoc = ae.associate(self.pacs_config['host'],
                             self.pacs_config['port'],
                             ae_title=self.pacs_config['ae_title'])
        if not assoc.is_established:
            raise Exception("Association rejected, aborted or never connected")
        return assoc

    def echo_scu(self):
        """Verify connectivity to the PACS server with a C-ECHO."""
        ae = self._build_ae()
        ae.add_requested_context(Verification)

        assoc = self._associate(ae)
        try:
            status = assoc.send_c_echo()
            if not status:
                raise Exception("C-ECHO request failed: no response from PACS")
            return status.Status
        finally:
            assoc.release()

    def send_to_pacs(self, dataset):
        """Send a DICOM dataset to the PACS server."""
        ae = self._build_ae()
        ae.add_requested_context(Verification)
        ae.add_requested_context(dataset.SOPClassUID)

        assoc = self._associate(ae)
        try:
            status = assoc.send_c_store(dataset)
            return status
        finally:
            assoc.release()

    def query_pacs(self, query_dataset):
        """Query the PACS server for studies/series/images."""
        ae = self._build_ae()
        ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)

        assoc = self._associate(ae)
        try:
            responses = assoc.send_c_find(query_dataset, PatientRootQueryRetrieveInformationModelFind)
            results = []
            for (status, identifier) in responses:
                if status and identifier is not None:
                    results.append(identifier)
            return results
        finally:
            assoc.release()

    def receive_from_pacs(self, study_instance_uid):
        """Ask the PACS to move a study to us (C-MOVE) based on StudyInstanceUID.

        This only delivers instances if a Storage SCP is already listening
        under `self.calling_ae_title` (see start_store_scp) and the PACS is
        configured to move to that AE title.
        """
        ae = self._build_ae()
        ae.add_requested_context(StudyRootQueryRetrieveInformationModelMove)

        identifier = Dataset()
        identifier.QueryRetrieveLevel = 'STUDY'
        identifier.StudyInstanceUID = study_instance_uid

        assoc = self._associate(ae)
        try:
            responses = assoc.send_c_move(
                identifier,
                self.calling_ae_title,
                StudyRootQueryRetrieveInformationModelMove,
            )
            for (status, identifier) in responses:
                if status:
                    logger.info("C-MOVE request status: 0x%04x", status.Status)
        finally:
            assoc.release()

    def handle_store(self, event):
        """Handle a C-STORE request by persisting the received instance."""
        dataset = event.dataset
        dataset.file_meta = event.file_meta

        self.storage_dir.mkdir(parents=True, exist_ok=True)
        file_path = self.storage_dir / f"{dataset.SOPInstanceUID}.dcm"
        try:
            dataset.save_as(file_path, write_like_original=False)
        except Exception:
            logger.exception("Failed to store received instance %s", dataset.SOPInstanceUID)
            return 0xA700  # Out of Resources

        return 0x0000  # Success

    def start_store_scp(self, port):
        """Start a Storage SCP server to receive DICOM files."""
        ae = self._build_ae()
        ae.add_supported_context(Verification)
        for context in AllStoragePresentationContexts:
            ae.add_supported_context(context.abstract_syntax)

        handlers = [(evt.EVT_C_STORE, self.handle_store)]

        ae.start_server(('', port), evt_handlers=handlers)
