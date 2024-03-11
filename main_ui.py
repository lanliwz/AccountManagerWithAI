import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtCore import Qt, QPoint

class DraggableSvgWidget(QSvgWidget):
    def __init__(self):
        super().__init__()
        self.dragging = False
        self.dragPosition = QPoint()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.dragPosition = event.position().toPoint() - self.pos()

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(event.position().toPoint() - self.dragPosition)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.centralWidget = QWidget()
        self.setCentralWidget(self.centralWidget)
        self.layout = QVBoxLayout()
        self.centralWidget.setLayout(self.layout)

        self.svgWidget = DraggableSvgWidget()
        self.layout.addWidget(self.svgWidget)

        self.open_file_dialog()

    def open_file_dialog(self):
        # options = QFileDialog.Options()
        fileName, _ = QFileDialog.getOpenFileName(self, "Open File", "", "Vector Graphics Files (*.svg);;All Files (*)")
        if fileName:
            self.display_svg(fileName)

    def display_svg(self, file_path):
        self.svgWidget.load(file_path)

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec())
