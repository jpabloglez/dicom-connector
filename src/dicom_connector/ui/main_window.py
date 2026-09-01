# ui/main_window.py
import logging
import threading
import tkinter as tk
from tkinter import filedialog, ttk

from dicom_connector.ui.tag_browser import TagBrowserWindow

logger = logging.getLogger(__name__)


class MainWindow(tk.Frame):
    def __init__(self, master, file_handler, network_handler, db_handler, anonymizer):
        super().__init__(master)
        self.file_handler = file_handler
        self.network_handler = network_handler
        self.db_handler = db_handler
        self.anonymizer = anonymizer

        self.create_widgets()

    def create_widgets(self):
        # File selection (used for Send to PACS)
        self.file_frame = ttk.LabelFrame(self, text="File Selection")
        self.file_frame.pack(fill=tk.X, padx=10, pady=10)

        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.browse_button = ttk.Button(self.file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5, pady=5)

        self.view_tags_button = ttk.Button(self.file_frame, text="View Tags", command=self.view_tags)
        self.view_tags_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Study Instance UID (used for Receive from PACS)
        self.receive_frame = ttk.LabelFrame(self, text="Receive (Study Instance UID)")
        self.receive_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.study_uid = tk.StringVar()
        self.study_uid_entry = ttk.Entry(self.receive_frame, textvariable=self.study_uid, width=50)
        self.study_uid_entry.pack(side=tk.LEFT, padx=5, pady=5)

        # Transmission buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.send_button = ttk.Button(self.button_frame, text="Send to PACS", command=self.send_to_pacs)
        self.send_button.pack(side=tk.LEFT, padx=5)

        self.receive_button = ttk.Button(self.button_frame, text="Receive from PACS", command=self.receive_from_pacs)
        self.receive_button.pack(side=tk.LEFT, padx=5)

        # Default on: de-identifying before transmission is the safer
        # default for medical data; sending raw is still one click away.
        self.anonymize_var = tk.BooleanVar(value=True)
        self.anonymize_check = ttk.Checkbutton(
            self.button_frame, text="Anonymize before sending", variable=self.anonymize_var,
        )
        self.anonymize_check.pack(side=tk.LEFT, padx=15)

        # Status and log area
        self.log_frame = ttk.LabelFrame(self, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def log(self, message):
        self.log_text.insert(tk.END, f"{message}\n")
        self.log_text.see(tk.END)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("DICOM files", "*.dcm")])
        if filename:
            self.file_path.set(filename)

    def view_tags(self):
        file_path = self.file_path.get()
        if not file_path:
            self.log("Please select a file first")
            return

        try:
            dataset = self.file_handler.read_dicom_file(file_path)
        except Exception as exc:
            self.log(f"Failed to read file for tag view: {exc}")
            return

        TagBrowserWindow(self, dataset, title=f"DICOM Tags - {file_path}")

    def _run_in_background(self, worker, on_done):
        """Run `worker()` off the Tk thread so associations don't freeze the UI.

        `on_done(result, error)` is marshalled back onto the Tk thread via
        `after()`, since Tk widgets aren't safe to touch from another thread.
        """
        buttons = (self.send_button, self.receive_button)
        for button in buttons:
            button.state(["disabled"])

        def target():
            try:
                result = worker()
            except Exception as exc:
                logger.exception("Background PACS operation failed")
                self.after(0, self._finish, on_done, None, exc, buttons)
            else:
                self.after(0, self._finish, on_done, result, None, buttons)

        threading.Thread(target=target, daemon=True).start()

    def _finish(self, on_done, result, error, buttons):
        for button in buttons:
            button.state(["!disabled"])
        on_done(result, error)

    def send_to_pacs(self):
        file_path = self.file_path.get()
        if not file_path:
            self.log("Please select a file first")
            return

        anonymize = self.anonymize_var.get()
        self.log(f"Sending file: {file_path} to PACS{' (anonymized)' if anonymize else ''}...")

        def worker():
            dataset = self.file_handler.read_dicom_file(file_path)
            if anonymize:
                dataset = self.anonymizer.anonymize(dataset)
            status = self.network_handler.send_to_pacs(dataset)
            # metadata/db record reflect what was actually transmitted, so
            # the local audit trail never holds identifiers that were
            # deliberately stripped before the data left this machine
            metadata = self.file_handler.get_dicom_metadata(dataset)
            self.db_handler.insert_dicom_record(metadata, file_path)
            return status

        def on_done(status, error):
            if error is not None:
                self.log(f"Send failed: {error}")
            else:
                self.log(f"Send complete, status: 0x{getattr(status, 'Status', 0):04X}")

        self._run_in_background(worker, on_done)

    def receive_from_pacs(self):
        study_uid = self.study_uid.get().strip()
        if not study_uid:
            self.log("Please enter a Study Instance UID first")
            return

        self.log(f"Requesting study {study_uid} from PACS...")

        def worker():
            return self.network_handler.receive_from_pacs(study_uid)

        def on_done(_result, error):
            if error is not None:
                self.log(f"Receive failed: {error}")
            else:
                self.log("Receive request completed - check the log/storage folder for incoming files")

        self._run_in_background(worker, on_done)
