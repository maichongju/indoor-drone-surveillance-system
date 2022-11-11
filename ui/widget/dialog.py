from enum import Enum, IntEnum

import numpy as np
from PyQt6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                             QPushButton, QVBoxLayout, QGroupBox, QMessageBox,
                             QInputDialog)

from general.utils import Axis, Position, is_number
from hub.drone import Drone
from hub.location import LOCATIONS, Location
from hub.path import PathList, Path
from ui.icon import Icon
from ui.widget.canvas import Canvas3DVispy, VispyPath
from ui.widget.list import LocationItem, LocationListWidget, PathDetailsListWidget, PathListWidget
from ui.widget.utils import StylePreset, set_label_style
from ui.widget.widget import PositionLabelEditSetWidget


class _Icon(Enum):
    CURRENT_LOCATION = Icon.DOWNLOAD
    ADD = Icon.PLUS_SIGN
    REMOVE = Icon.MINUS_SIGN
    EDIT = Icon.EDIT
    SAVE = Icon.DISKETTE
    UP = Icon.UP_ARROW
    DOWN = Icon.DOWN_ARROW


class GoToDialog(QDialog):
    """Dialog for go to a location. 
    """

    def __init__(self, drone: Drone, parent=None):
        super().__init__(parent)
        self._drone = drone
        self.setWindowTitle("Go to location")
        self.position = None
        self._setup_ui()
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self):

        layout = QVBoxLayout()
        self.setLayout(layout)

        center_layout = QHBoxLayout()
        layout.addLayout(center_layout)

        cord_layout = QVBoxLayout()
        center_layout.addLayout(cord_layout)

        cord_layout.addWidget(QLabel("Enter the destination location"))
        # location_layout = QHBoxLayout()
        # cord_layout.addLayout(location_layout)

        self.pos_x = PositionLabelEditSetWidget("X:", parent=self)
        self.pos_x.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.X))
        self.pos_x.btn.setToolTip("Get current X position")
        cord_layout.addWidget(self.pos_x)

        self.pos_y = PositionLabelEditSetWidget("Y:", parent=self)
        self.pos_y.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.Y))
        self.pos_y.btn.setToolTip("Get current Y position")
        cord_layout.addWidget(self.pos_y)

        self.pos_z = PositionLabelEditSetWidget("Z:", parent=self)
        self.pos_z.btn.clicked.connect(lambda: self._position_btn_click_callback(Axis.Z))
        self.pos_z.btn.setToolTip("Get current Z position")
        cord_layout.addWidget(self.pos_z)

        self.btn_add_to_list = QPushButton("Add")
        self.btn_add_to_list.clicked.connect(self._add_btn_click_callback)
        cord_layout.addWidget(self.btn_add_to_list)

        self.lbl_error = QLabel()
        set_label_style(self.lbl_error, StylePreset.WARNING_TEXT)
        cord_layout.addWidget(self.lbl_error)

        cord_layout.addStretch()

        # Layout for location list
        right_layout = QHBoxLayout()
        center_layout.addLayout(right_layout)

        self.location_list = LocationListWidget(self)
        right_layout.addWidget(self.location_list)

        self.location_list.setFixedSize(120, 150)
        self.location_list.itemDoubleClicked.connect(self._list_double_click_callback)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        btn_layout.addStretch()

        self.btn_ok = QPushButton("Go")
        self.btn_ok.clicked.connect(self.accept)
        btn_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

    def _list_double_click_callback(self, item: LocationItem):
        """Callback function for double click item

        Args:
            item (LocationItem): double clicked item
        """
        self.pos_x.le.setText(str(item.location.position.x))
        self.pos_y.le.setText(str(item.location.position.y))
        self.pos_z.le.setText(str(item.location.position.z))

    def _position_btn_click_callback(self, flag: Axis):
        """Position button callback function

        Args:
            flag (Position.Flag): Pos to modify
        """
        match flag:
            case Axis.X:
                self.pos_x.le.setText(str(self._drone.state.position.x))
            case Axis.Y:
                self.pos_y.le.setText(str(self._drone.state.position.y))
            case Axis.Z:
                self.pos_z.le.setText(str(self._drone.state.position.z))

    def _add_btn_click_callback(self):
        if (self._validate_input()):
            pos = Position(
                float(self.pos_x.le.text()),
                float(self.pos_y.le.text()),
                float(self.pos_z.le.text())
            )
            location = Location(position=pos)
            dialog = LocationEditDialog(location=location, parent=self, mode=LocationEditDialog.Mode.ADD)
            result = dialog.exec()
            if result == QDialog.DialogCode.Accepted:
                self.location_list.addItem(dialog.location)

    def _validate_input(self) -> bool:
        """Check if the position is valid. `True` if valid. `False` otherwise.

        Returns:
            bool: `True` if valid. `False` otherwise.
        """
        try:
            float(self.pos_x.le.text())
            float(self.pos_y.le.text())
            float(self.pos_z.le.text())
            return True
        except ValueError:
            return False

    def accept(self):
        if self._validate_input():
            self.position = Position(
                float(self.pos_x.le.text()),
                float(self.pos_y.le.text()),
                float(self.pos_z.le.text())
            )
            LOCATIONS.save(new_location=self.location_list.locations)
            super().accept()
        else:
            self.lbl_error.setText("Invalid X or Y or Z position")


class LocationDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self):

        self.setWindowIcon(Icon.get_icon(Icon.SETTING_WHEEL))
        self.setWindowTitle("Location Setting")

        layout = QHBoxLayout()
        self.setLayout(layout)

        self.locations_list = LocationListWidget(self)
        self.locations_list.setFixedSize(120, 180)
        self.locations_list.itemDoubleClicked.connect(self.show_edit_dialog)
        self.locations_list.itemClicked.connect(self._list_single_click)
        layout.addWidget(self.locations_list)

        btn_layout = QVBoxLayout()
        layout.addLayout(btn_layout)

        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._btn_add_onclick)
        btn_layout.addWidget(btn_add)

        self.btn_edit = QPushButton("Edit")
        self.btn_edit.setEnabled(False)
        self.btn_edit.clicked.connect(self._btn_edit_onclick)
        btn_layout.addWidget(self.btn_edit)

        self.btn_delete = QPushButton("Delete")
        self.btn_delete.setEnabled(False)
        self.btn_delete.clicked.connect(self._btn_delete_onclick)
        btn_layout.addWidget(self.btn_delete)

        btn_layout.addStretch()

        btn_save = QPushButton("Save")
        btn_save.setToolTip("Save the current location list")
        btn_save.clicked.connect(self._btn_save_onclick)
        btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setToolTip("Discard all the changes")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

    def show_edit_dialog(self, item: LocationItem):
        old_location_name = item.location.name
        dialog = LocationEditDialog(location=item.location,
                                    parent=self)
        value = dialog.exec()
        if value == QDialog.DialogCode.Accepted:
            item.update()
            self.locations_list.locations.update_location(old_location_name, dialog.location.name,
                                                          dialog.location.position)

    def _list_single_click(self, item: LocationItem):
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)

    def _btn_edit_onclick(self):
        self.show_edit_dialog(self.locations_list.currentItem())

    def _btn_delete_onclick(self):
        index = self.locations_list.currentRow()
        self.locations_list.remove(index)
        if self.locations_list.is_empty():
            self.btn_delete.setEnabled(False)
            self.btn_edit.setEnabled(False)

    def _btn_add_onclick(self):
        dialog = LocationEditDialog(parent=self, mode=LocationEditDialog.Mode.ADD)
        value = dialog.exec()
        if value == QDialog.DialogCode.Accepted:
            self.locations_list.addItem(dialog.location)

    def _btn_save_onclick(self):
        LOCATIONS.save(new_location=self.locations_list.locations)
        self.accept()


class LocationEditDialog(QDialog):
    class Mode(IntEnum):
        EDIT = 0,
        ADD = 1

    def __init__(self,
                 location: Location = None,
                 parent=None,
                 mode: Mode = Mode.EDIT,
                 show_name: bool = True):
        super().__init__(parent)
        self.location = location
        self._is_update = mode == self.Mode.EDIT
        self.setWindowTitle("Edit Location" if self._is_update else "Add Location")
        self._setup_ui(show_name)
        self._show_name = show_name
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self, show_name):

        layout = QVBoxLayout()
        self.setLayout(layout)

        if show_name:
            name_layout = QHBoxLayout()
            layout.addLayout(name_layout)
            name_layout.addWidget(QLabel("Name:"))
            self.le_name = QLineEdit(self.location.name if self.location is not None else "")
            name_layout.addWidget(self.le_name)

        location_layout = QHBoxLayout()
        layout.addLayout(location_layout)

        location_layout.addWidget(QLabel("X:"))
        self.le_x = QLineEdit(str(self.location.position.x if self.location is not None else ""))
        self.le_x.setMaximumWidth(100)
        location_layout.addWidget(self.le_x)
        location_layout.addWidget(QLabel("Y:"))
        self.le_y = QLineEdit(str(self.location.position.y if self.location is not None else ""))
        self.le_y.setMaximumWidth(100)
        location_layout.addWidget(self.le_y)

        location_layout.addWidget(QLabel("Z:"))
        self.le_z = QLineEdit(str(self.location.position.z if self.location is not None else ""))
        self.le_z.setMaximumWidth(100)
        location_layout.addWidget(self.le_z)

        btn_layout = QHBoxLayout()
        layout.addLayout(btn_layout)

        self.lbl_error = QLabel()
        set_label_style(self.lbl_error, StylePreset.WARNING_TEXT)
        btn_layout.addWidget(self.lbl_error)

        btn_layout.addStretch()
        btn_ok = QPushButton('Update' if self._is_update else 'Add')
        btn_ok.clicked.connect(self._btn_ok_on_click)
        btn_layout.addWidget(btn_ok)

        btn_cancel = QPushButton('Cancel')
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)

    def _btn_ok_on_click(self):
        """Ensure the input is valid. No duplicate name can exist in the list.
        """

        # Check the name.
        if self._show_name:
            if self.le_name.text() == "":
                self.lbl_error.setText("Name cannot be empty")
                return
            # For Location use case
            if self._is_update:

                if self.le_name.text() != self.location.name:
                    if LOCATIONS.existed(self.le_name.text()):
                        self.lbl_error.setText("Name already existed")
                        return

            else:
                if LOCATIONS.existed(self.le_name.text()):
                    self.lbl_error.setText("Name already existed")
                    return

        if self.le_x.text() == "" or self.le_y.text() == "" or self.le_z.text() == "":
            self.lbl_error.setText("Position cannot be empty")
            return

        if not is_number(self.le_x.text()) or not is_number(self.le_y.text()) or not is_number(self.le_z.text()):
            self.lbl_error.setText("Position must be a number")
            return

        self.location = Location(name=self.le_name.text() if self._show_name else "",
                                 position=self._get_position())

        super().accept()

    def _get_position(self):
        return Position(float(self.le_x.text()),
                        float(self.le_y.text()),
                        float(self.le_z.text()))


DEFAULT_PATH_LOCATION = 'paths.json'


class PathDialog(QDialog):
    class _Mode(IntEnum):
        PATH = 0
        PATH_DETAIL = 1

    def __init__(self, path_list: PathList, parent=None):
        super().__init__(parent)

        self._path_list = path_list
        self.current_path = None
        self._path_list_cur_index = -1
        self._canvas_path : VispyPath | None = None

        self.setWindowTitle("Path")
        self._setup_ui()
        self._set_enable_path_detail(False)
        self.setFixedSize(self.sizeHint())

    def _setup_ui(self):
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)

        self._path_list_ui = self._get_path_list_ui()
        self._path_detail_ui = self._get_path_detail_ui()

        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout)

        path_path_detail_layout = QHBoxLayout()
        path_path_detail_layout.addWidget(self._path_list_ui)
        path_path_detail_layout.addWidget(self._path_detail_ui)

        left_layout.addLayout(path_path_detail_layout)

        bottom_btn_layout = QHBoxLayout()
        left_layout.addLayout(bottom_btn_layout)

        bottom_btn_layout.addStretch()

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._btn_save_onclick)
        bottom_btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom_btn_layout.addWidget(btn_cancel)

        self._canvas = Canvas3DVispy(size=(500, 300))

        main_layout.addWidget(self._canvas.native)

    def _get_path_list_ui(self) -> QGroupBox:
        gb_path_list = QGroupBox("Paths")

        gb_path_list_layout = QHBoxLayout()
        gb_path_list.setLayout(gb_path_list_layout)

        self.path_list = PathListWidget(self._path_list)
        gb_path_list_layout.addWidget(self.path_list)
        self.path_list.setMaximumWidth(100)
        self.path_list.itemDoubleClicked.connect(lambda path: self._display_path(path.path))

        paths_btn_layout = QVBoxLayout()
        gb_path_list_layout.addLayout(paths_btn_layout)

        btn_add_path = QPushButton("")
        btn_add_path.setIcon(Icon.get_icon(_Icon.ADD.value))
        btn_add_path.clicked.connect(lambda: self._btn_add_on_click(self._Mode.PATH))
        paths_btn_layout.addWidget(btn_add_path)

        btn_remove_path = QPushButton("")
        btn_remove_path.setIcon(Icon.get_icon(_Icon.REMOVE.value))
        btn_remove_path.clicked.connect(lambda: self._btn_remove_on_click(self._Mode.PATH))
        paths_btn_layout.addWidget(btn_remove_path)

        paths_btn_layout.addStretch()

        return gb_path_list

    def _get_path_detail_ui(self) -> QGroupBox:
        gb_path_detail = QGroupBox("Path Detail")

        gb_path_detail_layout = QHBoxLayout()
        gb_path_detail.setLayout(gb_path_detail_layout)

        self.path_detail = PathDetailsListWidget()
        gb_path_detail_layout.addWidget(self.path_detail)
        self.path_detail.setMaximumWidth(150)
        self.path_detail.itemDoubleClicked.connect(lambda item: self._edit_location(item))
        self.path_detail.itemClicked.connect(lambda cur: self._highlight_pos(cur.location.position))

        path_detail_btn_layout = QVBoxLayout()
        gb_path_detail_layout.addLayout(path_detail_btn_layout)

        btn_add_path_detail = QPushButton("")
        btn_add_path_detail.setIcon(Icon.get_icon(_Icon.ADD.value))
        btn_add_path_detail.clicked.connect(lambda: self._btn_add_on_click(self._Mode.PATH_DETAIL))
        path_detail_btn_layout.addWidget(btn_add_path_detail)

        btn_remove_path_detail = QPushButton("")
        btn_remove_path_detail.setIcon(Icon.get_icon(_Icon.REMOVE.value))
        btn_remove_path_detail.clicked.connect(lambda: self._btn_remove_on_click(self._Mode.PATH_DETAIL))
        path_detail_btn_layout.addWidget(btn_remove_path_detail)

        btn_move_up = QPushButton("")
        btn_move_up.setIcon(Icon.get_icon(_Icon.UP.value))
        btn_move_up.clicked.connect(lambda: self.move_path_position("up"))
        path_detail_btn_layout.addWidget(btn_move_up)

        btn_move_down = QPushButton("")
        btn_move_down.setIcon(Icon.get_icon(_Icon.DOWN.value))
        btn_move_down.clicked.connect(lambda: self.move_path_position("down"))
        path_detail_btn_layout.addWidget(btn_move_down)

        btn_save_path_detail = QPushButton("")
        btn_save_path_detail.setIcon(Icon.get_icon(_Icon.SAVE.value))
        btn_save_path_detail.clicked.connect(self._btn_save_path_detail_on_click)
        path_detail_btn_layout.addWidget(btn_save_path_detail)

        path_detail_btn_layout.addStretch()

        return gb_path_detail

    def _display_path(self, path: Path):
        """
        Helper function that will set up everything needs to display a path. This will also
        display the path on the canvas.
        """
        if self._path_list_cur_index != -1 and self.path_detail.is_updated:
            reply = QMessageBox.question(self, "Unsaved Changes",
                                         "You have unsaved changes, do you want to save them?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
            if reply == QMessageBox.StandardButton.Yes:
                self._btn_save_path_detail_on_click()
            elif reply == QMessageBox.StandardButton.Cancel:
                self.path_detail.setCurrentRow(self._path_list_cur_index)
                return
        self._set_enable_path_detail(True)
        self._path_detail_ui.setTitle(f"Path Detail - {path.name}")
        self.path_detail.load(path)
        self._path_list_cur_index = self.path_list.currentRow()
        self._canvas_draw_path(path)
        self._canvas_path.clear_highlight_pos()

    def _canvas_draw_path(self, path: Path):
        """
        Helper function that will draw the path on the canvas. this will also remove the highlight point.
        """
        self._canvas_path = self._canvas.plot_path(path, vispy_path=self._canvas_path)

    def _set_enable_path_detail(self, enable: bool):
        self._path_detail_ui.setEnabled(enable)

    def _btn_add_on_click(self, mode: _Mode):
        if mode == self._Mode.PATH:
            path_name, ok = QInputDialog.getText(self, "Create New Path", "Enter the name of the path")
            if ok:
                if self.path_list.paths.name_exists(path_name):
                    QMessageBox.critical(self, "Error", "A path with this name already exists.")
                else:
                    path = Path(path_name)
                    self.path_list.paths.add_path(path)
                    self.path_list.addItem(path)
                    self.path_list.setCurrentRow(self.path_list.count() - 1)
                    self._display_path(path)
        elif mode == self._Mode.PATH_DETAIL:
            dialog = LocationEditDialog(parent=self, mode=LocationEditDialog.Mode.ADD, show_name=False)
            if dialog.exec():  # New path is created
                pos = dialog.location.position
                if self.path_detail.currentRow() == -1:
                    self.path_detail.addItem(pos)
                    self.path_detail.setCurrentRow(0)
                else:
                    self.path_detail.insertItem(self.path_detail.currentRow(), pos)
                    self.path_detail.setCurrentRow(self.path_detail.currentRow() - 1)

                self._set_path_detail_is_updated(True)
                self._update_path_detail_canvas()

    def _highlight_pos(self, pos: Position):
        print("highlight")
        if self._canvas_path is not None:
            self._canvas_path.set_highlight_pos(pos)

    def _update_path_detail_canvas(self):
        """
        Trigger a redrawn of the path on the canvas.
        """
        return
        if self._canvas_path is None:
            return # No path is currently displayed

        active_pos= None
        if self.path_detail.currentRow() != -1:
            active_pos = self.path_detail.currentItem().location.position  # type: ignore

        self._canvas_draw_path(self.path_detail.path)
        canvas_path = self._canvas_path  # type: VispyPath
        # Draw the active position
        if active_pos is not None:

            if canvas_path.highlight_pos is not None:
                canvas_path.highlight_pos.set_data(pos= np.array(active_pos.to_tuple()))
            else:
                canvas_path.highlight_pos = self._canvas.plot_point(active_pos)
        else:
            if canvas_path.highlight_pos is not None:
                canvas_path.highlight_pos.parent = None
                canvas_path.highlight_pos = None

    def _set_path_detail_is_updated(self, is_updated: bool):
        self.path_detail.is_updated = is_updated
        if is_updated:
            self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name} *")
        else:
            self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name}")

    def _btn_remove_on_click(self, mode: _Mode):
        if mode == self._Mode.PATH:
            if self.path_list.currentRow() == -1:
                return
            reply = QMessageBox.question(self, "Remove Path",
                                         f"Are you sure you want to remove this path ({self.path_list.currentItem().path.name})?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                current_index = self.path_list.currentRow()
                self.path_list.paths.remove_path_by_index(current_index)
                self.path_list.takeItem(current_index)
                if self.path_list.count() != 0:
                    if current_index == self.path_list.count():
                        current_index -= 1
                else:
                    current_index = -1
                self.path_list.setCurrentRow(current_index)
                if current_index != -1:
                    self._display_path(self.path_list.currentItem().path)
                else:
                    self._set_enable_path_detail(False)
                    self.clear_canvas()
                    self.path_detail.clear()
                    self._path_detail_ui.setTitle("Path Detail")
                    self._path_detail_ui.setEnabled(False)

        elif mode == self._Mode.PATH_DETAIL:
            if self.path_detail.currentRow() == -1:
                return
            current_index = self.path_detail.currentRow()
            self.path_detail.takeItem(current_index)

            self._set_path_detail_is_updated(True)

    def clear_canvas(self):
        if self._canvas_path is not None:
            self._canvas_path.clear()
            self._canvas_path = None

    def _edit_location(self, item: LocationItem):
        dialog = LocationEditDialog(location=item.location, parent=self, show_name=False)
        if dialog.exec():
            item.location = dialog.location
            item.update()
            self.path_detail.is_updated = True
            self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name} *")

    def move_path_position(self, direction: str):
        if direction == "up":
            pass
        elif direction == "down":
            pass

    def _btn_save_path_detail_on_click(self):
        self.path_detail.update_positions()
        self._path_detail_ui.setTitle(f"Path Detail - {self.path_detail.path.name}")
        self.path_detail.is_updated = False

    def _btn_save_onclick(self):
        try:
            with open(DEFAULT_PATH_LOCATION, 'w') as file:
                self._path_list.save(file)
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error when saving path ({e})")

    def _btn_no_onclick(self):
        super().reject()
