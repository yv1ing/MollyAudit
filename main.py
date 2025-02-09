import sys
from PyQt6.QtWidgets import QApplication
from app import load_config
from app.ui import MainWindow

app = QApplication(sys.argv)


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
    window.show()

    sys.exit(main())
