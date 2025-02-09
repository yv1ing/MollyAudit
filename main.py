import sys
import os
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication
from app import load_config
from app.ui import MainWindow

app = QApplication(sys.argv)


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def main():
    try:
        app.exec()
        return 0
    except Exception as e:
        print(e)
        return 1


if __name__ == '__main__':
    load_config()

    window = MainWindow()
    window.setWindowIcon(QIcon(resource_path('logo.ico')))
    window.show()

    sys.exit(main())
