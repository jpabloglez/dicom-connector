# ui/main_window.py
import tkinter as tk
from tkinter import filedialog, ttk

class MainWindow(tk.Frame):
    def __init__(self, master, file_handler, network_handler, db_handler):
        super().__init__(master)
        self.file_handler = file_handler
        self.network_handler = network_handler
        self.db_handler = db_handler

        self.create_widgets()

    def create_widgets(self):
        # File selection
        self.file_frame = ttk.LabelFrame(self, text="File Selection")
        self.file_frame.pack(fill=tk.X, padx=10, pady=10)

        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(self.file_frame, textvariable=self.file_path, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, pady=5)

        self.browse_button = ttk.Button(self.file_frame, text="Browse", command=self.browse_file)
        self.browse_button.pack(side=tk.LEFT, padx=5, pady=5)

        # Transmission buttons
        self.button_frame = ttk.Frame(self)
        self.button_frame.pack(fill=tk.X, padx=10, pady=10)

        self.send_button = ttk.Button(self.button_frame, text="Send to PACS", command=self.send_to_pacs)
        self.send_button.pack(side=tk.LEFT, padx=5)

        self.receive_button = ttk.Button(self.button_frame, text="Receive from PACS", command=self.receive_from_pacs)
        self.receive_button.pack(side=tk.LEFT, padx=5)

        # Status and log area
        self.log_frame = ttk.LabelFrame(self, text="Log")
        self.log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def browse_file(self):
        filename = filedialog.askopenfilename(filetypes=[("DICOM files", "*.dcm")])
        if filename:
            self.file_path.set(filename)

    def send_to_pacs(self):
        file_path = self.file_path.get()
        if file_path:
            # Here you would call the appropriate method from network_handler
            self.log_text.insert(tk.END, f"Sending file: {file_path} to PACS\n")
        else:
            self.log_text.insert(tk.END, "Please select a file first\n")

    def receive_from_pacs(self):
        # Here you would call the appropriate method from network_handler
        self.log_text.insert(tk.END, "Receiving files from PACS\n")