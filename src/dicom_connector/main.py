# main.py
import logging
import threading
import tkinter as tk

from dicom_connector import config
from dicom_connector.database.db_handler import DatabaseHandler
from dicom_connector.dicom.anonymizer import DatasetAnonymizer
from dicom_connector.dicom.file_handler import DicomFileHandler
from dicom_connector.dicom.network import DicomNetwork
from dicom_connector.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def _start_store_scp_in_background(network_handler, port):
    """Run the Storage SCP on a daemon thread for the app's lifetime.

    Without this listening, a PACS C-MOVE has nowhere to push instances to:
    "Receive from PACS" would associate, request the move, and then just
    wait forever with nothing arriving.
    """
    def run():
        try:
            network_handler.start_store_scp(port)
        except Exception:
            logger.exception("Storage SCP failed to start on port %s", port)

    threading.Thread(target=run, daemon=True, name="storage-scp").start()


def main():
    logging.basicConfig(level=logging.INFO)

    root = tk.Tk()
    root.title("DICOM Application")

    # Initialize components
    db_handler = DatabaseHandler(config.DB_CONFIG)
    db_handler.create_tables()  # Ensure tables are created

    file_handler = DicomFileHandler()
    network_handler = DicomNetwork(config.PACS_CONFIG, storage_dir=config.STORAGE_DIR)
    _start_store_scp_in_background(network_handler, config.PACS_CONFIG['store_scp_port'])

    # One shared Anonymizer for the app's lifetime: reusing it across sends
    # keeps identifiers (StudyInstanceUID, PatientID, etc.) mapped
    # consistently across files from the same study/patient.
    anonymizer = DatasetAnonymizer()

    # Create main window
    main_window = MainWindow(
        root, file_handler, network_handler, db_handler, anonymizer,
        orthanc_url=config.ORTHANC_HTTP_CONFIG['url'],
    )
    main_window.pack(fill=tk.BOTH, expand=True)

    root.mainloop()


if __name__ == "__main__":
    main()
