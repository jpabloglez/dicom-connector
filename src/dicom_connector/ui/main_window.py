# ui/main_window.py
import logging
import threading
import tkinter as tk
from datetime import date, datetime
from tkinter import filedialog, ttk

from dicom_connector.ui.image_viewer import ImageViewerWindow
from dicom_connector.ui.pacs_browser import PacsBrowserWindow
from dicom_connector.ui.tag_browser import TagBrowserWindow

logger = logging.getLogger(__name__)


class MainWindow(tk.Frame):
    def __init__(self, master, file_handler, network_handler, db_handler, anonymizer, orthanc_api=None):
        super().__init__(master)
        self.file_handler = file_handler
        self.network_handler = network_handler
        self.db_handler = db_handler
        self.anonymizer = anonymizer
        self.orthanc_api = orthanc_api

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

        self.preview_button = ttk.Button(self.file_frame, text="Preview", command=self.preview_image)
        self.preview_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Study Instance UID (used for Receive from PACS)
        self.receive_frame = ttk.LabelFrame(self, text="Receive (Study Instance UID)")
        self.receive_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.study_uid = tk.StringVar()
        self.study_uid_entry = ttk.Entry(self.receive_frame, textvariable=self.study_uid, width=50)
        self.study_uid_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.browse_pacs_button = ttk.Button(
            self.receive_frame, text="Browse", command=self.browse_pacs,
        )
        self.browse_pacs_button.pack(side=tk.LEFT, padx=5, pady=5)

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

        # Received files: auto-refreshed after each successful receive (and
        # once at startup), scoped to today - selecting a row loads it into
        # File Selection above, so View Tags/Preview/Send all just work
        self.received_frame = ttk.LabelFrame(self, text="Received Files (Today)")
        self.received_frame.pack(fill=tk.BOTH, padx=10, pady=(0, 10))

        received_columns = ("time", "patient", "study_date", "modality", "description")
        self.received_tree = ttk.Treeview(
            self.received_frame, columns=received_columns, show="headings", height=5,
        )
        for column, heading, width in (
            ("time", "Received", 80), ("patient", "Patient", 150), ("study_date", "Study Date", 90),
            ("modality", "Modality", 70), ("description", "Description", 220),
        ):
            self.received_tree.heading(column, text=heading)
            self.received_tree.column(column, width=width, anchor="center" if column != "description" else "w")
        self.received_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.received_tree.bind("<<TreeviewSelect>>", self._on_received_file_selected)

        received_scrollbar = ttk.Scrollbar(
            self.received_frame, orient="vertical", command=self.received_tree.yview,
        )
        self.received_tree.configure(yscrollcommand=received_scrollbar.set)
        received_scrollbar.pack(side=tk.LEFT, fill=tk.Y, pady=5)

        self.refresh_received_button = ttk.Button(
            self.received_frame, text="Refresh", command=self.refresh_received_files,
        )
        self.refresh_received_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Status and log area
        self.log_frame = ttk.LabelFrame(self, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.refresh_received_files()  # show anything already received today, e.g. from an earlier run

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

    def preview_image(self):
        file_path = self.file_path.get()
        if not file_path:
            self.log("Please select a file first")
            return

        try:
            dataset = self.file_handler.read_dicom_file(file_path)
            ImageViewerWindow(self, self.file_handler, dataset, title=f"DICOM Preview - {file_path}")
        except Exception as exc:
            self.log(f"Failed to preview file: {exc}")

    def browse_pacs(self):
        if not self.orthanc_api:
            self.log("Orthanc API not configured")
            return

        PacsBrowserWindow(self, self.orthanc_api, on_select=self._on_pacs_study_selected)

    def _on_pacs_study_selected(self, study_uid):
        # Browse exists specifically to pick a study *to receive* - fetch
        # it immediately rather than making the user notice the UID landed
        # in the field and separately click Receive from PACS themselves.
        self.study_uid.set(study_uid)
        self.log(f"Selected study for receive: {study_uid}")
        self.receive_from_pacs()

    def refresh_received_files(self):
        """Repopulate the Received Files list from storage_dir, scoped to
        today. Called at startup and after each successful receive."""
        self.received_tree.delete(*self.received_tree.get_children())

        storage_dir = self.network_handler.storage_dir
        if not storage_dir.exists():
            return

        try:
            paths = sorted(storage_dir.glob("*.dcm"), key=lambda p: p.stat().st_mtime, reverse=True)
        except OSError as exc:
            self.log(f"Could not list received files: {exc}")
            return

        # Deliberately naive/local, not timezone-aware: "today" here means
        # the user's local wall-clock day (matching what they see on their
        # desktop), and os.stat().st_mtime is inherently local-naive too -
        # making just one side tz-aware would introduce a UTC/local
        # mismatch rather than fix one.
        today = date.today()  # noqa: DTZ011
        for path in paths:
            try:
                received_at = datetime.fromtimestamp(path.stat().st_mtime)  # noqa: DTZ006
            except OSError:
                continue
            if received_at.date() != today:
                continue

            try:
                dataset = self.file_handler.read_dicom_file(path)
                metadata = self.file_handler.get_dicom_metadata(dataset)
            except Exception:
                metadata = {"PatientName": "?", "StudyDate": "?", "Modality": "?", "StudyDescription": "?"}

            self.received_tree.insert(
                "", "end", iid=str(path),
                values=(
                    received_at.strftime("%H:%M:%S"), metadata["PatientName"], metadata["StudyDate"],
                    metadata["Modality"], metadata["StudyDescription"],
                ),
            )

    def _on_received_file_selected(self, _event=None):
        selection = self.received_tree.selection()
        if not selection:
            return
        file_path = selection[0]  # iid is the full path, set in refresh_received_files
        self.file_path.set(file_path)
        self.log(f"Selected received file: {file_path}")

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
                self.log("Receive request completed")
                self.refresh_received_files()
                self._select_most_recently_received_file()

        self._run_in_background(worker, on_done)

    def _select_most_recently_received_file(self):
        """Auto-select the newest row in Received Files (refresh_received_files
        sorts newest-first) so View Tags/Preview/Send are immediately ready
        against whatever was just received, with no extra click."""
        rows = self.received_tree.get_children("")
        if rows:
            self.received_tree.selection_set(rows[0])  # fires <<TreeviewSelect>> -> sets file_path
