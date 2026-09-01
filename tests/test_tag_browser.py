# test_tag_browser.py
from pydicom.dataelem import DataElement
from pydicom.dataset import Dataset
from pydicom.sequence import Sequence

from dicom_connector.ui.tag_browser import build_tag_tree, format_value


def make_dataset():
    ds = Dataset()
    ds.PatientName = "Test^Patient"
    ds.PatientID = "123"

    item = Dataset()
    item.StudyInstanceUID = "1.2.3.4.5"
    ds.ReferencedStudySequence = Sequence([item])

    ds.PixelData = b"\x00" * 1000
    return ds


def nodes_by_keyword(nodes):
    return {node.keyword: node for node in nodes}


def test_flat_fields_render_as_plain_values():
    nodes = nodes_by_keyword(build_tag_tree(make_dataset()))

    assert nodes["PatientName"].value == "Test^Patient"
    assert nodes["PatientName"].tag == "(0010,0010)"
    assert nodes["PatientName"].vr == "PN"
    assert nodes["PatientID"].value == "123"


def test_sequence_recurses_into_item_children():
    nodes = nodes_by_keyword(build_tag_tree(make_dataset()))
    seq_node = nodes["ReferencedStudySequence"]

    assert seq_node.vr == "SQ"
    assert seq_node.value == "1 item"
    assert len(seq_node.children) == 1

    item_node = seq_node.children[0]
    assert item_node.keyword == "Item 1"

    item_fields = nodes_by_keyword(item_node.children)
    assert item_fields["StudyInstanceUID"].value == "1.2.3.4.5"


def test_pixel_data_shows_size_not_raw_bytes():
    nodes = nodes_by_keyword(build_tag_tree(make_dataset()))
    assert nodes["PixelData"].value == "<1000 bytes>"


def test_long_text_values_are_truncated():
    # built directly as a DataElement (VR "UT", genuinely unbounded) rather
    # than through Dataset attribute assignment, to avoid tripping pydicom's
    # VR-length validation for a VR that wouldn't actually hold 500 chars
    elem = DataElement(0x0040A160, "UT", "x" * 500)

    text = format_value(elem)
    assert len(text) <= 128
    assert text.endswith("...")


def test_unknown_tag_falls_back_to_private_tag_label():
    ds = Dataset()
    ds.add_new(0x00090010, "LO", "Private Creator")  # unrecognized private tag
    nodes = build_tag_tree(ds)

    assert nodes[0].keyword == "Private Tag"
    assert nodes[0].tag == "(0009,0010)"
