# ui/pacs_browser.py
"""Toplevel window for finding a study to receive by searching Orthanc's
own REST API by Patient ID, instead of needing to already know a raw
Study Instance UID.
"""
import tkinter as tk
from tkinter import ttk

from dicom_connector.dicom.studies import fetch_studies, matches_patient_filter


class PacsBrowserWindow(tk.Toplevel):
    def __init__(self, master, orthanc_api, on_select, title="Browse PACS Studies"):
        super().__init__(master)
        self.orthanc_api = orthanc_api
        self.on_select = on_select
        self.title(title)
        self.geometry("720x400")

        search_frame = ttk.Frame(self)
        search_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(search_frame, text="Patient ID:").pack(side=tk.LEFT)
        self.patient_id_var = tk.StringVar()
        entry = ttk.Entry(search_frame, textvariable=self.patient_id_var, width=30)
        entry.pack(side=tk.LEFT, padx=5)
        entry.bind("<Return>", lambda _event: self.search())
        entry.focus_set()

        self.search_button = ttk.Button(search_frame, text="Search", command=self.search)
        self.search_button.pack(side=tk.LEFT, padx=5)

        columns = ("patient_id", "patient_name", "study_date", "description", "series")
        self.tree = ttk.Treeview(self, columns=columns, show="headings")
        for column, heading, width in (
            ("patient_id", "Patient ID", 100), ("patient_name", "Patient Name", 160),
            ("study_date", "Study Date", 90), ("description", "Description", 220),
            ("series", "Series", 60),
        ):
            self.tree.heading(column, text=heading)
            self.tree.column(column, width=width, anchor="center" if column == "series" else "w")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 5))
        self.tree.bind("<Double-1>", lambda _event: self.use_selected())

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.use_button = ttk.Button(button_frame, text="Use Selected", command=self.use_selected)
        self.use_button.pack(side=tk.LEFT)

        self.status_var = tk.StringVar()
        ttk.Label(button_frame, textvariable=self.status_var).pack(side=tk.LEFT, padx=10)

        self.search()  # show everything on open, not an empty dialog

    def search(self):
        patient_id = self.patient_id_var.get().strip()
        self.status_var.set("Searching...")
        self.search_button.state(["disabled"])
        self.update_idletasks()

        try:
            studies = fetch_studies(self.orthanc_api)
        except Exception as exc:
            self.status_var.set(f"Search failed: {exc}")
            self.search_button.state(["!disabled"])
            return

        studies = [s for s in studies if matches_patient_filter(s, patient_id)]

        self.tree.delete(*self.tree.get_children())
        for study in studies:
            self.tree.insert(
                "", "end", iid=study["study_instance_uid"],
                values=(
                    study["patient_id"] or "-", study["patient_name"] or "-",
                    study["study_date"] or "-", study["study_description"] or "-",
                    study["series_count"],
                ),
            )

        self.status_var.set(f"{len(studies)} study(ies) found")
        self.search_button.state(["!disabled"])

    def use_selected(self):
        selection = self.tree.selection()
        if not selection:
            self.status_var.set("Select a study first")
            return
        study_uid = selection[0]  # iid is the Study Instance UID, set in search()
        self.on_select(study_uid)
        self.destroy()
