# ui/tag_browser.py
"""Pure dataset-to-tree logic, kept separate from the Tk widget so it's
testable without a display, plus the Toplevel window that renders it.
"""
import tkinter as tk
from dataclasses import dataclass, field
from tkinter import ttk

MAX_VALUE_LENGTH = 128


@dataclass
class TagNode:
    tag: str
    keyword: str
    vr: str
    value: str
    children: list["TagNode"] = field(default_factory=list)


def format_value(elem):
    """Render one DataElement's value as display text.

    Sequences show a count (their detail lives in child nodes instead) and
    any bulk binary value (PixelData and friends) shows its size rather
    than being dumped as garbled text.
    """
    if elem.VR == "SQ":
        count = len(elem.value)
        return f"{count} item{'s' if count != 1 else ''}"

    value = elem.value
    if isinstance(value, bytes):
        return f"<{len(value)} bytes>"

    text = str(value)
    if len(text) > MAX_VALUE_LENGTH:
        text = text[:MAX_VALUE_LENGTH - 3] + "..."
    return text


def build_tag_tree(dataset):
    """Convert a pydicom Dataset into a list of TagNode, recursing into
    sequences as nested "Item N" nodes."""
    nodes = []
    for elem in dataset:
        node = TagNode(
            tag=f"({elem.tag.group:04X},{elem.tag.element:04X})",
            keyword=elem.keyword or "Private Tag",
            vr=elem.VR or "",
            value=format_value(elem),
        )
        if elem.VR == "SQ":
            for index, item in enumerate(elem.value, start=1):
                item_node = TagNode(tag="", keyword=f"Item {index}", vr="", value="")
                item_node.children = build_tag_tree(item)
                node.children.append(item_node)
        nodes.append(node)
    return nodes


class TagBrowserWindow(tk.Toplevel):
    def __init__(self, master, dataset, title="DICOM Tags"):
        super().__init__(master)
        self.title(title)
        self.geometry("800x600")

        columns = ("tag", "vr", "value")
        self.tree = ttk.Treeview(self, columns=columns, show="tree headings")
        self.tree.heading("#0", text="Keyword")
        self.tree.heading("tag", text="Tag")
        self.tree.heading("vr", text="VR")
        self.tree.heading("value", text="Value")
        self.tree.column("#0", width=250)
        self.tree.column("tag", width=100, anchor="center")
        self.tree.column("vr", width=50, anchor="center")
        self.tree.column("value", width=380)

        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)

        self._insert_nodes("", build_tag_tree(dataset))

    def _insert_nodes(self, parent, nodes):
        for node in nodes:
            item_id = self.tree.insert(
                parent, "end", text=node.keyword,
                values=(node.tag, node.vr, node.value),
            )
            if node.children:
                self._insert_nodes(item_id, node.children)
