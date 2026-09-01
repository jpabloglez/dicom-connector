# ui/image_viewer.py
"""Toplevel window showing a DICOM dataset's pixel data, with window/level
sliders for grayscale data. Rendering logic lives in
DicomFileHandler.get_preview_image() so it's testable without a display;
this widget is a thin wrapper around it.
"""
import tkinter as tk
from tkinter import ttk

from PIL import ImageTk


class ImageViewerWindow(tk.Toplevel):
    def __init__(self, master, file_handler, dataset, title="DICOM Preview"):
        super().__init__(master)
        self.file_handler = file_handler
        self.dataset = dataset
        self.title(title)

        self.canvas = tk.Canvas(self, background="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill=tk.X, padx=10, pady=10)

        self._photo = None  # keep a reference - Tk drops PhotoImage otherwise

        result = self.file_handler.get_preview_image(dataset)
        self._is_grayscale = result.window_center is not None

        if self._is_grayscale:
            self._build_window_level_controls(result.window_center, result.window_width)

        self._render(result.image)

    def _build_window_level_controls(self, initial_center, initial_width):
        self.center_var = tk.DoubleVar(value=initial_center)
        self.width_var = tk.DoubleVar(value=initial_width)

        center_range = max(abs(initial_center) * 2, initial_width * 2, 100)
        width_range = max(initial_width * 4, 100)

        ttk.Label(self.controls_frame, text="Center").grid(row=0, column=0, sticky="w")
        self.center_scale = ttk.Scale(
            self.controls_frame, from_=-center_range, to=center_range,
            variable=self.center_var, command=self._on_slider_change,
        )
        self.center_scale.grid(row=0, column=1, sticky="ew", padx=5)

        ttk.Label(self.controls_frame, text="Width").grid(row=1, column=0, sticky="w")
        self.width_scale = ttk.Scale(
            self.controls_frame, from_=1, to=width_range,
            variable=self.width_var, command=self._on_slider_change,
        )
        self.width_scale.grid(row=1, column=1, sticky="ew", padx=5)

        self.controls_frame.columnconfigure(1, weight=1)

    def _on_slider_change(self, _value=None):
        result = self.file_handler.get_preview_image(
            self.dataset, window_center=self.center_var.get(), window_width=self.width_var.get(),
        )
        self._render(result.image)

    def _render(self, pil_image):
        self._photo = ImageTk.PhotoImage(pil_image)
        self.canvas.delete("all")
        self.canvas.config(width=pil_image.width, height=pil_image.height)
        self.canvas.create_image(0, 0, anchor="nw", image=self._photo)
