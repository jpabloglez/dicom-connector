# main.py
import tkinter as tk
from ui.main_window import MainWindow
from dicom.file_handler import DicomFileHandler
from dicom.network import DicomNetwork
from database.db_handler import DatabaseHandler
import config

def main():
    root = tk.Tk()
    root.title("DICOM Application")

    # Initialize components
    db_handler = DatabaseHandler(config.DB_CONFIG)
    db_handler.create_tables()  # Ensure tables are created

    file_handler = DicomFileHandler()
    network_handler = DicomNetwork(config.PACS_CONFIG)

    # Create main window
    main_window = MainWindow(root, file_handler, network_handler, db_handler)
    main_window.pack(fill=tk.BOTH, expand=True)

    root.mainloop()

if __name__ == "__main__":
    main()