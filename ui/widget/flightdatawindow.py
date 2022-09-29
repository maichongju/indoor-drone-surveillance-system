from __future__ import annotations



# Must import this before importing matplotlib
from PyQt6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget, QPushButton, QFileDialog

import pandas as pd
# from hub import Hub
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

# from general.utils import ensure_folder_exist
import time 


EXPORT_FOLDER = 'export'

class FlightDataWindow(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent= parent)
        self.setWindowTitle("Flight Data")
        # self._hub = hub
        self._setup_ui()
        self.setFixedSize(self.sizeHint())
        
    def _setup_ui(self):
        main_layout = QHBoxLayout(self)
        self.setLayout(main_layout)
        
        canvas_layout = QVBoxLayout()
        main_layout.addLayout(canvas_layout)
        
        self.canvas = Canvas()
        canvas_layout.addWidget(self.canvas)
        
        toolbar_layout = QVBoxLayout()
        main_layout.addLayout(toolbar_layout)
        
        btn_load = QPushButton("Load")
        btn_load.clicked.connect(self._load_btn_on_click)
        toolbar_layout.addWidget(btn_load)
        
        btn_clear = QPushButton("Clear")
        btn_clear.clicked.connect(lambda: self.canvas.clear())
        toolbar_layout.addWidget(btn_clear)
                
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(lambda: self.canvas.save())
        toolbar_layout.addWidget(btn_save)
        
        toolbar_layout.addStretch()
        
        btn_top_down = QPushButton("Top Down")
        btn_top_down.clicked.connect(lambda: self.canvas.to_top_down())
        toolbar_layout.addWidget(btn_top_down)
        
        btn_side_view = QPushButton("Side View (Y)")
        btn_side_view.clicked.connect(lambda: self.canvas.to_side_view_Y())
        toolbar_layout.addWidget(btn_side_view)
        
        btn_side_view = QPushButton("Side View (X)")
        btn_side_view.clicked.connect(lambda: self.canvas.to_side_view_X())
        toolbar_layout.addWidget(btn_side_view)
        
        
    def _load_btn_on_click(self):
        # Add file dialog (use QFileDialog)
        file_path,_ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        
        if file_path == '':
            return 
        # file_path = 'logs/flightdataexample.csv'
        df = pd.read_csv(file_path)
        cols = ['stateEstimate.x','stateEstimate.y','stateEstimate.z']
        values = []
        for col in cols:
            values.append(df[col].values.tolist())
        self.canvas.plot(values)
        
        
class Canvas(FigureCanvas):
    def __init__(self,):
        self.fig = Figure(figsize=(7, 7), dpi=100)
        super().__init__(self.fig)
        self.ax = self.fig.add_subplot(111, projection='3d')
        self.ax.set_xlabel('Y')
        self.ax.set_ylabel('X')
        self.ax.set_zlabel('Z')
        
    def plot(self, points):
        self.ax.clear()
        size = len(points[0])
        for i in range(size):
            self.ax.scatter(points[0][i], -points[1][i], points[2][i])

        
        self.draw()
            
    def to_top_down(self):
        self.ax.view_init(-90, -90)
        self.draw()
        
    def to_side_view_Y(self):
        self.ax.view_init(0, -90)
        self.draw()
        
    def to_side_view_X(self):
        self.ax.view_init(0, 0)
        self.draw()
        
    def clear(self):
        self.ax.clear()
        self.draw()
        
    def save(self):
        # ensure_folder_exist(EXPORT_FOLDER)
        cur_time = time.strftime('%Y%m%d%H%M%S')
        self.fig.savefig(f'{EXPORT_FOLDER}/{cur_time}.png')
        
        
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    window = FlightDataWindow()
    window.show()
    sys.exit(app.exec())
   
    
        
        