# dicom/network.py
"""
This DicomNetwork class provides methods for sending DICOM 
files to PACS, querying PACS, and receiving files from PACS. 
It also includes a basic implementation of a Storage SCP 
server to receive DICOM files.
"""
from pynetdicom import AE, evt, AllStoragePresentationContexts
from pynetdicom.sop_class import PatientRootQueryRetrieveInformationModelFind, Verification

class DicomNetwork:
    def __init__(self, pacs_config):
        self.pacs_config = pacs_config
        self.ae = AE(ae_title=pacs_config.get('calling_ae_title', 'MYAETITLE'))

    def echo_scu(self):
        """Verify connectivity to the PACS server with a C-ECHO."""
        self.ae.add_requested_context(Verification)

        assoc = self.ae.associate(self.pacs_config['host'],
                                  self.pacs_config['port'],
                                  ae_title=self.pacs_config['ae_title'])

        if assoc.is_established:
            status = assoc.send_c_echo()
            assoc.release()
            if status:
                return status.Status
            raise Exception("C-ECHO request failed: no response from PACS")
        else:
            raise Exception("Association rejected, aborted or never connected")

    def send_to_pacs(self, dataset):
        """Send a DICOM dataset to the PACS server."""
        self.ae.add_requested_context('1.2.840.10008.1.1')
        self.ae.add_requested_context(dataset.SOPClassUID)

        assoc = self.ae.associate(self.pacs_config['host'], 
                                  self.pacs_config['port'], 
                                  ae_title=self.pacs_config['ae_title'])
        
        if assoc.is_established:
            status = assoc.send_c_store(dataset)
            assoc.release()
            return status
        else:
            raise Exception("Association rejected, aborted or never connected")

    def query_pacs(self, query_dataset):
        """Query the PACS server for studies/series/images."""
        self.ae.add_requested_context(PatientRootQueryRetrieveInformationModelFind)

        assoc = self.ae.associate(self.pacs_config['host'], 
                                  self.pacs_config['port'], 
                                  ae_title=self.pacs_config['ae_title'])

        if assoc.is_established:
            responses = assoc.send_c_find(query_dataset, PatientRootQueryRetrieveInformationModelFind)
            results = []
            for (status, identifier) in responses:
                if status:
                    results.append(identifier)
            assoc.release()
            return results
        else:
            raise Exception("Association rejected, aborted or never connected")

    def receive_from_pacs(self, study_instance_uid):
        """Receive DICOM files from PACS based on StudyInstanceUID."""
        self.ae.add_requested_context('1.2.840.10008.5.1.4.1.2.2.1')
        self.ae.add_requested_context('1.2.840.10008.5.1.4.1.2.2.2')
        self.ae.supported_contexts = AllStoragePresentationContexts

        assoc = self.ae.associate(self.pacs_config['host'], 
                                  self.pacs_config['port'], 
                                  ae_title=self.pacs_config['ae_title'])

        if assoc.is_established:
            # Implement C-MOVE operation here
            # This is a simplified version and may need to be adjusted based on your PACS server's requirements
            responses = assoc.send_c_move(study_instance_uid, '1.2.840.10008.5.1.4.1.2.2.2')
            for (status, identifier) in responses:
                if status:
                    print('C-MOVE request status: 0x{0:04x}'.format(status.Status))
            assoc.release()
        else:
            raise Exception("Association rejected, aborted or never connected")

    @staticmethod
    def handle_store(event):
        """Handle a C-STORE request."""
        return 0x0000  # Success

    def start_store_scp(self, port):
        """Start a Storage SCP server to receive DICOM files."""
        self.ae.add_supported_context('1.2.840.10008.1.1')
        for context in AllStoragePresentationContexts:
            self.ae.add_supported_context(context.abstract_syntax)

        handlers = [(evt.EVT_C_STORE, self.handle_store)]

        self.ae.start_server(('', port), evt_handlers=handlers)