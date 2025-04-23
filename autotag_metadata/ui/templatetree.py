"""
Treeview of the teaplate dictionary
"""

# ********************************************************************
#  This file is part of autotag-metadata.
#
#        Copyright (C) 2024 Johannes Hermann
#
#  autotag-metadata is free software: you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  autotag-metadata is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with autotag-metadata. If not, see
#  <https://www.gnu.org/licenses/>.
# ********************************************************************
from collections import deque

from PyQt6.QtGui import QStandardItem, QStandardItemModel
from PyQt6.QtWidgets import QTreeView, QVBoxLayout, QWidget


class TemplateTree(QWidget):
    def __init__(self, data):
        super(TemplateTree, self).__init__()
        self.tree = QTreeView(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tree)
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Key", "Value", "Type"])

        self.tree.setModel(self.model)
        # self.tree.hideColumn(2)
        self.import_from_dict(data)

    def import_from_dict(self, data, root=None):
        self.model.setRowCount(0)
        if root is None:
            root = self.model.invisibleRootItem()
        available_parents = {}
        data = self.dict_to_model(data)
        values = deque(data)
        while values:
            value = values.popleft()

            if value["parent_id"] == 0:
                parent = root
            else:
                if value["parent_id"] not in available_parents:
                    values.append(value)
                    continue
                parent = available_parents[value["parent_id"]]
            id = value["id"]
            parent.appendRow(
                [
                    QStandardItem(str(value["key"])),
                    QStandardItem(str(value["val"])),
                    QStandardItem(str(value["type"])),
                ]
            )
            available_parents[id] = parent.child(parent.rowCount() - 1)
        self.tree.expandAll()

    def dict_to_model(self, dictionary: dict, parent_id=None) -> list:
        items = []
        if parent_id is None:
            parent_id = 0

        id = parent_id + 1

        for key, val in dictionary.items():
            if isinstance(val, dict):
                items.append(
                    {
                        "parent_id": parent_id,
                        "id": id,
                        "key": key,
                        "val": "",
                        "type": str(type(val)),
                    }
                )
                items.extend(self.dict_to_model(val, id))
            elif type(val) in (list, set, tuple):
                items.append(
                    {
                        "parent_id": parent_id,
                        "id": id,
                        "key": key,
                        "val": "",
                        "type": str(type(val)),
                    }
                )
                items.extend(self.list_to_model(val, id))
            else:
                items.append(
                    {
                        "parent_id": parent_id,
                        "id": id,
                        "key": key,
                        "val": val,
                        "type": str(type(val)),
                    }
                )
            id += 1
        return items

    def list_to_model(self, dict_list: list, parent_id=None) -> list:
        items = []
        if parent_id is None:
            parent_id = 0

        id = parent_id + 1

        for key, val in enumerate(dict_list):
            if isinstance(val, dict):
                items.append(
                    {
                        "parent_id": parent_id,
                        "id": id,
                        "key": key,
                        "val": "",
                        "type": str(type(val)),
                    }
                )
                items.extend(self.dict_to_model(val, id))
            elif type(val) in (list, set, tuple):
                items.append(
                    {
                        "parent_id": parent_id,
                        "id": id,
                        "key": key,
                        "val": "",
                        "type": str(type(val)),
                    }
                )
                items.extend(self.list_to_model(val, id))
            else:
                items.append(
                    {
                        "parent_id": parent_id,
                        "id": id,
                        "key": key,
                        "val": val,
                        "type": str(type(val)),
                    }
                )
            id += 1
        return items

    def to_dict(self):
        return self.recurse_items(self.model)

    def recurse_items(self, item, item_type=None):
        if item is not None:
            if item.hasChildren():
                temp_dict = {}
                temp_list = []
                for i in range(item.rowCount()):
                    if isinstance(item, QStandardItemModel):
                        item_type = str(type(dict()))
                        child_key = item.item(i, 0)
                        child_val = item.item(i, 1)
                        child_item_type = item.item(i, 2)
                    else:
                        child_key = item.child(i, 0)
                        child_val = item.child(i, 1)
                        child_item_type = item.child(i, 2)
                    try:
                        if child_item_type.text() == str(type(int())):
                            temp_dict[child_key.text()] = int(child_val.text())
                            temp_list.append(int(child_val.text()))
                        elif child_item_type.text() == str(type(float())):
                            temp_dict[child_key.text()] = float(child_val.text())
                            temp_list.append(float(child_val.text()))
                        elif child_item_type.text() == str(type(str())):
                            try:  # break when number is input in str field
                                if child_key.text() not in ["crystallographicOrientation"]:
                                    float(child_val.text())
                                    return None
                                else:
                                    temp_dict[child_key.text()] = child_val.text()
                                    temp_list.append(child_val.text())
                            except ValueError:
                                temp_dict[child_key.text()] = child_val.text()
                                temp_list.append(child_val.text())
                        else:
                            child = self.recurse_items(child_key, item_type=child_item_type.text())
                            temp_dict[child_key.text()] = child
                            temp_list.append(child)
                    except ValueError:
                        return None

                if item_type == str(type(dict())):
                    return temp_dict
                elif item_type == str(type(list())):
                    return temp_list
