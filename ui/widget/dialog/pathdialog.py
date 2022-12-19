from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QMessageBox

from map.path import PathList
from ui.widget.widget import PathEditWidget

DEFAULT_PATH_LOCATION = 'paths.json'


class PathDialog(QDialog):

    def __init__(self, path_list: PathList, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Path Edit")
        self._path_list = path_list
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        self.path_widget = PathEditWidget(self._path_list)
        layout.addWidget(self.path_widget)

        bottom_btn_layout = QHBoxLayout()
        layout.addLayout(bottom_btn_layout)

        bottom_btn_layout.addStretch()

        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self._btn_save_onclick)
        bottom_btn_layout.addWidget(btn_save)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        bottom_btn_layout.addWidget(btn_cancel)

    def _btn_save_onclick(self):
        self.path_widget.save()
        try:
            with open(DEFAULT_PATH_LOCATION, 'w') as file:
                self._path_list.save(file)
            super().accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error when saving path ({e})")

    def _btn_no_onclick(self):
        super().reject()
