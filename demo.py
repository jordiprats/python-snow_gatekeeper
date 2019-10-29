import time
import pysnow

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QGridLayout, QWidget, QCheckBox, QSystemTrayIcon, \
    QSpacerItem, QSizePolicy, QMenu, QAction, QStyle, qApp
from PyQt5.QtCore import QSize

from threading import Thread

snow_instance = "nttcom"
snow_username = ""
snow_password = ""
main_window = None


class Login(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(Login, self).__init__(parent)
        self.textName = QtWidgets.QLineEdit(self)
        self.textPass = QtWidgets.QLineEdit(self)
        self.textPass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.buttonLogin = QtWidgets.QPushButton('Login', self)
        self.buttonLogin.clicked.connect(self.handleLogin)
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.textName)
        layout.addWidget(self.textPass)
        layout.addWidget(self.buttonLogin)

    def handleLogin(self):
        global snow_instance, snow_username, snow_password
        snow_username = self.textName.text()
        snow_password = self.textPass.text()

        try:
            client = pysnow.Client(instance=snow_instance, user=snow_username, password=snow_password)
            response = (client
                .resource(api_path='/table/sys_user')
                .get(query={'user_name': snow_username})
                .one())
            self.accept()
        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, 'Error', 'Bad user or password: '+str(e))


class MainWindow(QMainWindow):
    check_box = None
    tray_icon = None

    def run_snow_incident_checks(self):
        global snow_instance, snow_username, snow_password
        #while True:
        c = pysnow.client.Client(instance=snow_instance, user=snow_username, password=snow_password)

        qb = (pysnow.QueryBuilder()
                .field('assigned_to').is_empty()
                .AND()
                .field('assignment_group.name').equals('MS Team 2')
                .AND()
                .field('active').equals('true')
                )

        incident = c.resource(api_path='/table/incident')
        response = incident.get(query=qb)

        incident_count = len(response.all())

        if incident_count==0:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_DialogApplyButton))
        else:
            self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_MessageBoxCritical))

        #FIX THIS:
        self.tray_icon.showMessage(
            "Tray Program",
            "Incident count: "+str(incident_count),
            QSystemTrayIcon.Information,
            2000
        )

    # Override the class constructor
    def __init__(self):
        # Be sure to call the super class method
        QMainWindow.__init__(self)

        self.setMinimumSize(QSize(480, 80))             # Set sizes
        self.setWindowTitle("System Tray Application")  # Set a title
        central_widget = QWidget(self)                  # Create a central widget
        self.setCentralWidget(central_widget)           # Set the central widget

        grid_layout = QGridLayout(self)         # Create a QGridLayout
        central_widget.setLayout(grid_layout)   # Set the layout into the central widget
        grid_layout.addWidget(QLabel("Application, which can minimize to Tray", self), 0, 0)

        # Add a checkbox, which will depend on the behavior of the program when the window is closed
        self.check_box = QCheckBox('Minimize to Tray')
        self.check_box.setChecked(1)
        grid_layout.addWidget(self.check_box, 1, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)

        # Init QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))

        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)
        hide_action = QAction("Hide", self)
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(qApp.quit)
        tray_menu = QMenu()
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        self.run_snow_incident_checks()

    # Override closeEvent, to intercept the window closing event
    # The window will be closed only if there is no check mark in the check box
    def closeEvent(self, event):
        if self.check_box.isChecked():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "Tray Program",
                "Application was minimized to Tray",
                QSystemTrayIcon.Information,
                2000
            )


if __name__ == "__main__":
    global main_window
    import sys

    app = QApplication(sys.argv)
    login = Login()

    if login.exec_() == QtWidgets.QDialog.Accepted:
        main_window = MainWindow()
        sys.exit(app.exec())
