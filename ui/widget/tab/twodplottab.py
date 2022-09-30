import pandas as pd
from ast import main
from ui.widget.tab.tab import Tab
from PyQt6.QtWidgets import QGridLayout, QWidget, QScrollArea, QHBoxLayout
from PyQt6.QtCore import Qt
from ui.widget.canvas import CanvasWidget


class TwoDPlotTab(Tab):
    def __init__(self, parent=None):
        super().__init__('2D Plot', parent=parent)

        widget = QWidget() # Dummy widget to hold the layout
        main_layout = QGridLayout(self)
        widget.setLayout(main_layout)
        
        
        dummy_layout = QHBoxLayout()
        scroll = QScrollArea()
        scroll.setWidget(widget)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        
        dummy_layout.addWidget(scroll)
        self.setLayout(dummy_layout)
        
        
        self.height_canvas = CanvasWidget('time', 'height', title='Height')
        main_layout.addWidget(self.height_canvas, 0, 0)

        self.xy_top_canvas = CanvasWidget('y', 'x', title='Top View', invert_x=True)
        main_layout.addWidget(self.xy_top_canvas, 0, 1)
        
    def plot(self, df: pd.DataFrame, file_name: str):
        
        size = len(df.index)
        
        # Height plot
        height_data = [[i for i in range(size)], df['stateEstimate.z'].to_list()]
        self.height_canvas.plot(height_data, file_name=file_name)
        
        # Top View Plot
        top_view_data = [df['stateEstimate.y'].to_list(), df['stateEstimate.x'].to_list()]
        self.xy_top_canvas.plot(top_view_data, file_name=file_name)
        
    def clear(self):
        self.height_canvas.clear()
        self.xy_top_canvas.clear()     
    
        
        
        
        
        
