# dicom/file_handler.py
from collections import namedtuple

import numpy as np
import pydicom
from PIL import Image
from pydicom.pixel_data_handlers.util import apply_modality_lut

# `image` is always set; `window_center`/`window_width` are the values that
# were actually used to produce it (None for RGB data, which isn't windowed)
# - a caller building sliders can initialize them from this instead of
# guessing.
PreviewResult = namedtuple("PreviewResult", ["image", "window_center", "window_width"])


def _first(value):
    """Unwrap a pydicom multi-valued element (e.g. WindowCenter with VM>1)
    to its first value as a plain float."""
    if hasattr(value, "__iter__") and not isinstance(value, str):
        value = next(iter(value))
    return float(value)


class DicomFileHandler:
    def __init__(self):
        pass

    def read_dicom_file(self, file_path):
        try:
            return pydicom.dcmread(file_path)
        except Exception as e:
            raise Exception(f"Error reading DICOM file: {e!s}")

    def write_dicom_file(self, dataset, file_path):
        try:
            dataset.save_as(file_path)
        except Exception as e:
            raise Exception(f"Error writing DICOM file: {e!s}")

    def get_dicom_metadata(self, dataset):
        metadata = {
            "PatientName": str(dataset.PatientName) if 'PatientName' in dataset else "N/A",
            "StudyDate": str(dataset.StudyDate) if 'StudyDate' in dataset else "N/A",
            "Modality": str(dataset.Modality) if 'Modality' in dataset else "N/A",
            "StudyDescription": str(dataset.StudyDescription) if 'StudyDescription' in dataset else "N/A"
        }
        return metadata

    def get_preview_image(self, dataset, window_center=None, window_width=None):
        """Render dataset.pixel_array as a display-ready 8-bit PIL Image.

        For grayscale data (MONOCHROME1/2), applies the Modality LUT
        (RescaleSlope/RescaleIntercept) then windows to 8-bit using
        `window_center`/`window_width` if given, else the dataset's own
        WindowCenter/WindowWidth, else an automatic full-range stretch.
        RGB/YBR data is passed through unwindowed. Compressed transfer
        syntaxes (JPEG, JPEG2000, ...) are decoded via the pylibjpeg
        plugins declared as project dependencies; anything pydicom still
        can't decode raises a clear ValueError rather than a raw crash.

        Limitation (MVP): only the first frame of multi-frame data.
        """
        if 'PixelData' not in dataset:
            raise ValueError("Dataset has no PixelData to preview")

        try:
            pixels = dataset.pixel_array
        except Exception as exc:
            raise ValueError(
                "Could not decode pixel data - the transfer syntax may be "
                f"compressed and unsupported without extra codecs: {exc}"
            ) from exc

        number_of_frames = int(dataset.get('NumberOfFrames', 1) or 1)
        if number_of_frames > 1:
            pixels = pixels[0]

        samples_per_pixel = int(dataset.get('SamplesPerPixel', 1))
        if samples_per_pixel >= 3:
            image_array = pixels if pixels.dtype == np.uint8 else pixels.astype(np.uint8)
            return PreviewResult(image=Image.fromarray(image_array, mode="RGB"),
                                  window_center=None, window_width=None)

        values = apply_modality_lut(pixels, dataset)

        if window_center is None or window_width is None:
            ds_center = dataset.get('WindowCenter')
            ds_width = dataset.get('WindowWidth')
            if ds_center is not None and ds_width is not None:
                window_center = _first(ds_center)
                window_width = _first(ds_width)

        if window_center is None or not window_width:
            low, high = float(values.min()), float(values.max())
            window_center = (low + high) / 2
            window_width = max(high - low, 1.0)
        else:
            low = window_center - window_width / 2
            high = window_center + window_width / 2
            if high <= low:
                high = low + 1

        clipped = np.clip(values, low, high)
        normalized = ((clipped - low) / (high - low) * 255.0).astype(np.uint8)

        if dataset.get('PhotometricInterpretation', '') == 'MONOCHROME1':
            normalized = 255 - normalized

        return PreviewResult(image=Image.fromarray(normalized, mode="L"),
                              window_center=window_center, window_width=window_width)
