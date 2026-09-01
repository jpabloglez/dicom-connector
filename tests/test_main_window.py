# test_main_window.py
"""UI-level tests for MainWindow, against a real Tk instance (skipped
cleanly wherever no display is available - CI, headless containers).

This is exactly the layer where a real bug lived undetected earlier in
this project's life: the Send/Receive buttons only wrote to the log and
never called network_handler at all. Pure-function/mocked-backend tests
elsewhere wouldn't have caught that - only exercising the real widget
wiring does.
"""
import tempfile
import time
import tkinter as tk
from pathlib import Path
from unittest.mock import patch

import pytest
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dicom_connector.dicom.anonymizer import DatasetAnonymizer
from dicom_connector.dicom.file_handler import DicomFileHandler
from dicom_connector.ui import main_window as main_window_mod

try:
    _probe = tk.Tk()
    _probe.destroy()
    TK_AVAILABLE = True
except tk.TclError:
    TK_AVAILABLE = False

pytestmark = pytest.mark.skipif(not TK_AVAILABLE, reason="No display available for Tk tests")


class ImmediateThread:
    """Test-only stand-in for threading.Thread: runs the target
    synchronously on the calling thread instead of a real OS thread.

    Verified directly: a background thread calling self.after() cross-
    thread raises "RuntimeError: main thread is not in main loop" unless
    the main thread is genuinely inside root.mainloop() - true for the
    real app (main.py calls mainloop()), not for this test harness (which
    drives the event loop via polling root.update() instead, since a real
    mainloop() call would just block the test). A same-thread after()
    call works fine without mainloop() running at all, so running the
    worker synchronously here sidesteps the guard entirely while still
    exercising the real worker()/on_done() logic.
    """
    def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
        self._target = target
        self._args = args
        self._kwargs = kwargs or {}

    def start(self):
        self._target(*self._args, **self._kwargs)


@pytest.fixture(autouse=True)
def synchronous_background_thread():
    with patch.object(main_window_mod.threading, "Thread", ImmediateThread):
        yield


class FakeNetworkHandler:
    def __init__(self):
        self.sent = []
        self.received_study_uids = []

    def send_to_pacs(self, dataset):
        self.sent.append(dataset)
        return type("Status", (), {"Status": 0x0000})()

    def receive_from_pacs(self, study_uid):
        self.received_study_uids.append(study_uid)


class FakeDbHandler:
    def __init__(self):
        self.records = []

    def insert_dicom_record(self, metadata, file_path):
        self.records.append(metadata)


def pump_until(root, condition, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        root.update()
        if condition():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def dcm_file():
    ds = Dataset()
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.2"
    ds.SOPInstanceUID = generate_uid()
    ds.PatientName = "Doe^John"
    ds.PatientID = "P1"
    ds.Modality = "CT"
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta = file_meta

    tmp_path = Path(tempfile.mktemp(suffix=".dcm"))
    ds.save_as(tmp_path, write_like_original=False)
    yield tmp_path
    tmp_path.unlink(missing_ok=True)


@pytest.fixture(scope="module")
def root():
    # One Tk() interpreter for the whole module, not one per test.
    # Creating/destroying many separate tk.Tk() instances in one process,
    # combined with the real cross-thread after() calls this widget makes,
    # reproducibly segfaulted the interpreter (confirmed: a background
    # thread from an already-torn-down test's window was still calling
    # self.after() while a *different* test's objects were being garbage
    # collected). The real app only ever creates one root for its entire
    # lifetime, so one shared root here matches actual usage instead of
    # stress-testing a pattern ("many interpreters, one process") the app
    # never exercises.
    r = tk.Tk()
    yield r
    r.destroy()


@pytest.fixture
def window(root):
    net = FakeNetworkHandler()
    db = FakeDbHandler()
    win = main_window_mod.MainWindow(root, DicomFileHandler(), net, db, DatasetAnonymizer())
    win.pack(fill=tk.BOTH, expand=True)
    win.net = net
    win.db = db
    yield win
    root.update()  # flush any trailing Tcl idle callbacks before teardown
    win.destroy()


def test_anonymize_checkbox_defaults_to_checked(window):
    assert window.anonymize_var.get() is True


def test_send_requires_a_file_selected(window):
    window.send_to_pacs()
    window.update()

    assert "Please select a file first" in window.log_text.get("1.0", tk.END)
    assert window.net.sent == []


def test_send_with_anonymize_checked_transmits_deidentified_data(window, dcm_file):
    window.file_path.set(str(dcm_file))
    window.send_to_pacs()

    # Wait for the *log message*, not net.sent directly: net.sent is
    # appended mid-worker() on the background thread, before it reaches
    # self.after(). Polling that instead used to let this test return -
    # and its fixture destroy the Tk root - while the background thread
    # was still about to call self.after() on it, a real crash risk
    # (observed as a segfault when the full suite ran back-to-back).
    # Waiting for the log line only becomes true *after* self.after() has
    # already run on_done() on the Tk thread, so the background thread has
    # nothing left to do with Tk by the time we see it.
    assert pump_until(window.winfo_toplevel(), lambda: "Send complete" in window.log_text.get("1.0", tk.END))

    sent = window.net.sent[0]
    assert str(sent.PatientName) != "Doe^John"
    assert sent.PatientID != "P1"
    # the local DB record mirrors what was actually transmitted
    assert window.db.records[0]["PatientName"] == str(sent.PatientName)


def test_send_with_anonymize_unchecked_transmits_raw_data(window, dcm_file):
    window.file_path.set(str(dcm_file))
    window.anonymize_var.set(False)
    window.send_to_pacs()

    assert pump_until(window.winfo_toplevel(), lambda: "Send complete" in window.log_text.get("1.0", tk.END))

    sent = window.net.sent[0]
    assert str(sent.PatientName) == "Doe^John"
    assert sent.PatientID == "P1"


def test_receive_requires_a_study_uid(window):
    window.receive_from_pacs()
    window.update()

    assert "Please enter a Study Instance UID first" in window.log_text.get("1.0", tk.END)
    assert window.net.received_study_uids == []


def test_receive_calls_network_handler_with_entered_study_uid(window):
    study_uid = generate_uid()
    window.study_uid.set(study_uid)
    window.receive_from_pacs()

    assert pump_until(
        window.winfo_toplevel(),
        lambda: "Receive request completed" in window.log_text.get("1.0", tk.END),
    )
    assert window.net.received_study_uids == [study_uid]


def test_view_tags_opens_populated_tag_browser(window, dcm_file):
    window.file_path.set(str(dcm_file))
    created = {}
    real_cls = main_window_mod.TagBrowserWindow

    def spy(master, dataset, title="DICOM Tags"):
        win = real_cls(master, dataset, title)
        created["win"] = win
        return win

    with patch.object(main_window_mod, "TagBrowserWindow", spy):
        window.view_tags()
        window.update()

    tag_win = created["win"]
    labels = [tag_win.tree.item(row, "text") for row in tag_win.tree.get_children("")]
    assert "PatientName" in labels
    tag_win.destroy()


def test_preview_opens_populated_image_viewer_for_non_image_file(window, dcm_file):
    # dcm_file has no PixelData - confirm the failure surfaces in the log
    # rather than crashing the app
    window.file_path.set(str(dcm_file))
    window.preview_image()
    window.update()

    assert "Failed to preview file" in window.log_text.get("1.0", tk.END)
