import sys
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow

def main():
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("Test App")
    window.setCentralWidget(QLabel("PySide6 is working!"))
    window.resize(400, 200)
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
