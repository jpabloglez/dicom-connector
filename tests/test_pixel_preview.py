# test_pixel_preview.py
import numpy as np
import pytest
from PIL import Image
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

from dicom_connector.dicom.file_handler import DicomFileHandler


def _attach_file_meta(ds):
    ds.SOPClassUID = "1.2.840.10008.5.1.4.1.1.7"  # Secondary Capture, good enough for a test fixture
    ds.SOPInstanceUID = generate_uid()
    ds.is_little_endian = True
    ds.is_implicit_VR = False
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = ds.SOPClassUID
    file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian
    ds.file_meta = file_meta
    return ds


def make_grayscale_dataset(rows=32, cols=32, photometric="MONOCHROME2",
                            rescale_slope=1, rescale_intercept=0,
                            window_center=None, window_width=None):
    ds = Dataset()
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 1
    ds.PhotometricInterpretation = photometric
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0
    ds.RescaleSlope = rescale_slope
    ds.RescaleIntercept = rescale_intercept
    if window_center is not None:
        ds.WindowCenter = window_center
        ds.WindowWidth = window_width

    gradient = np.tile(np.linspace(0, 4000, cols, dtype=np.uint16), (rows, 1))
    ds.PixelData = gradient.tobytes()
    return _attach_file_meta(ds)


def make_rgb_dataset(rows=8, cols=8):
    ds = Dataset()
    ds.Rows = rows
    ds.Columns = cols
    ds.SamplesPerPixel = 3
    ds.PhotometricInterpretation = "RGB"
    ds.BitsAllocated = 8
    ds.BitsStored = 8
    ds.HighBit = 7
    ds.PixelRepresentation = 0
    ds.PlanarConfiguration = 0
    arr = np.zeros((rows, cols, 3), dtype=np.uint8)
    arr[..., 0] = 200  # solid red-ish image
    ds.PixelData = arr.tobytes()
    return _attach_file_meta(ds)


def test_missing_pixel_data_raises_clear_error():
    ds = Dataset()
    with pytest.raises(ValueError, match="PixelData"):
        DicomFileHandler().get_preview_image(ds)


def test_explicit_window_clips_and_normalizes_to_0_255():
    ds = make_grayscale_dataset(rescale_slope=1, rescale_intercept=-1000)
    result = DicomFileHandler().get_preview_image(ds, window_center=40, window_width=400)

    assert isinstance(result.image, Image.Image)
    assert result.image.mode == "L"
    arr = np.array(result.image)
    assert arr.min() == 0
    assert arr.max() == 255
    assert result.window_center == 40
    assert result.window_width == 400


def test_defaults_to_dataset_own_window_when_none_given():
    ds = make_grayscale_dataset(window_center=40, window_width=400)
    result = DicomFileHandler().get_preview_image(ds)

    assert result.window_center == 40
    assert result.window_width == 400


def test_auto_stretches_when_no_window_anywhere():
    ds = make_grayscale_dataset()  # no WindowCenter/Width set at all
    result = DicomFileHandler().get_preview_image(ds)

    arr = np.array(result.image)
    # full linear gradient input -> auto full-range stretch should touch both ends
    assert arr.min() == 0
    assert arr.max() == 255
    assert result.window_center is not None
    assert result.window_width is not None


def test_monochrome1_is_inverted():
    ds1 = make_grayscale_dataset(photometric="MONOCHROME1", rescale_slope=1, rescale_intercept=-1000)
    ds2 = make_grayscale_dataset(photometric="MONOCHROME2", rescale_slope=1, rescale_intercept=-1000)

    r1 = DicomFileHandler().get_preview_image(ds1, window_center=40, window_width=400)
    r2 = DicomFileHandler().get_preview_image(ds2, window_center=40, window_width=400)

    arr1 = np.array(r1.image)
    arr2 = np.array(r2.image)
    assert np.array_equal(arr1, 255 - arr2)


def test_rgb_dataset_passes_through_without_windowing():
    ds = make_rgb_dataset()
    result = DicomFileHandler().get_preview_image(ds)

    assert result.image.mode == "RGB"
    assert result.window_center is None
    assert result.window_width is None
    arr = np.array(result.image)
    assert arr[0, 0, 0] == 200


def test_multiframe_uses_only_first_frame():
    ds = make_grayscale_dataset(window_center=40, window_width=400)
    ds.NumberOfFrames = 2
    single_frame = np.frombuffer(ds.PixelData, dtype=np.uint16).reshape(ds.Rows, ds.Columns)
    second_frame = np.zeros_like(single_frame)
    ds.PixelData = np.stack([single_frame, second_frame]).tobytes()

    result = DicomFileHandler().get_preview_image(ds, window_center=40, window_width=400)
    arr = np.array(result.image)

    # first frame is the real gradient (varies across columns), not the all-zero second frame
    assert arr.max() > arr.min()
