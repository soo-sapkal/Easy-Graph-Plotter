import sys
import pandas as pd
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QComboBox, QLabel, QHBoxLayout, QTableView, QSplitter
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas, NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure


class ZoomableCanvas(FigureCanvas):
    def __init__(self, figure):
        super().__init__(figure)
        self.setFocusPolicy(True)
        self.setFocus()
        self.figure = figure
        self.ax = self.figure.add_subplot(111)

        self.zoom_factor = 1.2
        self.panning = False
        self.pan_start = None

        self.mpl_connect("scroll_event", self.zoom)
        self.mpl_connect("button_press_event", self.start_pan)
        self.mpl_connect("motion_notify_event", self.pan)
        self.mpl_connect("button_release_event", self.end_pan)

    def zoom(self, event):
        ax = self.ax
        xdata = event.xdata
        ydata = event.ydata

        if xdata is None or ydata is None:
            return

        cur_xlim = ax.get_xlim()
        cur_ylim = ax.get_ylim()

        x_left = xdata - cur_xlim[0]
        x_right = cur_xlim[1] - xdata
        y_bottom = ydata - cur_ylim[0]
        y_top = cur_ylim[1] - ydata

        scale_factor = 1 / self.zoom_factor if event.button == 'up' else self.zoom_factor

        new_xlim = [xdata - x_left * scale_factor, xdata + x_right * scale_factor]
        new_ylim = [ydata - y_bottom * scale_factor, ydata + y_top * scale_factor]

        ax.set_xlim(new_xlim)
        ax.set_ylim(new_ylim)
        self.draw()

    def start_pan(self, event):
        if event.button == 2:  # Middle mouse button
            self.panning = True
            self.pan_start = (event.x, event.y)
            self.start_xlim = self.ax.get_xlim()
            self.start_ylim = self.ax.get_ylim()

    def pan(self, event):
        if self.panning and event.xdata is not None and event.ydata is not None and self.pan_start:
            dx = event.x - self.pan_start[0]
            dy = event.y - self.pan_start[1]

            inv = self.ax.transData.inverted()
            start_data = inv.transform(self.pan_start)
            current_data = inv.transform((event.x, event.y))

            dx_data = start_data[0] - current_data[0]
            dy_data = start_data[1] - current_data[1]

            xlim = self.start_xlim[0] + dx_data, self.start_xlim[1] + dx_data
            ylim = self.start_ylim[0] + dy_data, self.start_ylim[1] + dy_data

            self.ax.set_xlim(xlim)
            self.ax.set_ylim(ylim)
            self.draw()

    def end_pan(self, event):
        if event.button == 2:
            self.panning = False
            self.pan_start = None


class LinePlotter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("EASY-PLOTTER")
        self.df = None

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Header with Load Button
        header_layout = QHBoxLayout()
        self.load_button = QPushButton("Load CSV")
        self.load_button.clicked.connect(self.load_csv)
        header_layout.addWidget(self.load_button)
        header_layout.addStretch()
        self.layout.addLayout(header_layout)

        # Controls for X/Y axis
        self.controls_layout = QHBoxLayout()
        self.x_label = QLabel("X-axis:")
        self.y_label = QLabel("Y-axis:")
        self.x_dropdown = QComboBox()
        self.y_dropdown = QComboBox()
        self.x_dropdown.currentIndexChanged.connect(self.plot_graph)
        self.y_dropdown.currentIndexChanged.connect(self.plot_graph)

        self.controls_layout.addWidget(self.x_label)
        self.controls_layout.addWidget(self.x_dropdown)
        self.controls_layout.addWidget(self.y_label)
        self.controls_layout.addWidget(self.y_dropdown)
        self.layout.addLayout(self.controls_layout)

        # Splitter for Table and Plot
        self.splitter = QSplitter(Qt.Horizontal)
        self.layout.addWidget(self.splitter)

        self.table_view = QTableView()
        self.splitter.addWidget(self.table_view)

        self.figure = Figure()
        self.canvas = ZoomableCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        plot_widget = QWidget()
        plot_layout = QVBoxLayout()
        plot_layout.addWidget(self.toolbar)
        plot_layout.addWidget(self.canvas)
        plot_widget.setLayout(plot_layout)
        self.splitter.addWidget(plot_widget)

    def load_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open CSV", "", "CSV Files (*.csv)")
        if path:
            self.df = pd.read_csv(path)
            self.x_dropdown.clear()
            self.y_dropdown.clear()
            self.x_dropdown.addItems(self.df.columns)
            self.y_dropdown.addItems(self.df.columns)
            self.populate_table()
            self.plot_graph()

    def populate_table(self):
        if self.df is not None:
            model = QStandardItemModel()
            model.setHorizontalHeaderLabels(self.df.columns.tolist())

            for row in self.df.itertuples(index=False):
                items = [QStandardItem(str(cell)) for cell in row]
                model.appendRow(items)

            self.table_view.setModel(model)
            self.table_view.selectionModel().selectionChanged.connect(self.handle_row_selection)

    def plot_graph(self):
        if self.df is not None:
            x_col = self.x_dropdown.currentText()
            y_col = self.y_dropdown.currentText()
            if x_col and y_col:
                self.figure.clear()
                self.canvas.ax = self.figure.add_subplot(111)
                self.canvas.ax.plot(self.df[x_col], self.df[y_col], marker='o')
                self.canvas.ax.set_title(f"{y_col} vs {x_col}")
                self.canvas.ax.set_xlabel(x_col)
                self.canvas.ax.set_ylabel(y_col)
                self.canvas.draw()

    def handle_row_selection(self, selected, deselected):
        if not selected.indexes():
            return

        index = selected.indexes()[0].row()
        x_col = self.x_dropdown.currentText()
        y_col = self.y_dropdown.currentText()

        if self.df is not None and x_col and y_col:
            self.figure.clear()
            self.canvas.ax = self.figure.add_subplot(111)
            self.canvas.ax.plot(self.df[x_col], self.df[y_col], marker='o')

            # Highlight selected point
            x_val = self.df[x_col].iloc[index]
            y_val = self.df[y_col].iloc[index]
            self.canvas.ax.plot(x_val, y_val, 'ro', markersize=10, label="Selected Point")
            self.canvas.ax.axvline(x_val, color='gray', linestyle='--', alpha=0.5)
            self.canvas.ax.axhline(y_val, color='gray', linestyle='--', alpha=0.5)

            self.canvas.ax.set_title(f"{y_col} vs {x_col}")
            self.canvas.ax.set_xlabel(x_col)
            self.canvas.ax.set_ylabel(y_col)
            self.canvas.ax.legend()
            self.canvas.draw()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LinePlotter()
    window.resize(1200, 700)
    window.show()
    sys.exit(app.exec_())
