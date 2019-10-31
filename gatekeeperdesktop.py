import time
import pysnow

from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5 import QtCore

from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QGridLayout, QWidget, QCheckBox, QSystemTrayIcon, \
    QSpacerItem, QSizePolicy, QMenu, QAction, QStyle, qApp
from PyQt5.QtCore import QSize


snow_instance = ""
snow_username = ""
snow_password = ""
debug=0
main_window = None


class Login(QtWidgets.QDialog):
    def __init__(self, parent=None):
        global snow_instance, snow_username, snow_password, debug
        super(Login, self).__init__(parent)

        self.setWindowTitle("Login")
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        self.settings = QtCore.QSettings()

        self.textInstance = QtWidgets.QLineEdit(self)
        self.textName = QtWidgets.QLineEdit(self)
        self.textPass = QtWidgets.QLineEdit(self)
        self.textPass.setEchoMode(QtWidgets.QLineEdit.Password)

        self.textInstance.setText(self.settings.value("snow_instance"))
        self.textName.setText(self.settings.value("snow_username"))
        self.textPass.setText(self.settings.value("snow_password"))

        self.debug_checkbox = QCheckBox('debug')
        if self.settings.value("debug") == '1':
            self.debug_checkbox.setChecked(1)
            debug=True
        else:
            self.debug_checkbox.setChecked(0)
            debug=False

        self.buttonLogin = QtWidgets.QPushButton('Login', self)
        self.buttonLogin.clicked.connect(self.handleLogin)
        layout = QtWidgets.QVBoxLayout(self)

        layout.addWidget(QLabel("instance:", self))
        layout.addWidget(self.textInstance)
        layout.addWidget(QLabel("username:", self))
        layout.addWidget(self.textName)
        layout.addWidget(QLabel("password:", self))
        layout.addWidget(self.textPass)
        layout.addWidget(QLabel("debug:", self))
        layout.addWidget(self.debug_checkbox)

        layout.addWidget(self.buttonLogin)

    def handleLogin(self):
        global snow_instance, snow_username, snow_password, debug
        snow_instance = self.textInstance.text()
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

        self.settings.setValue("snow_instance", snow_instance)
        self.settings.setValue("snow_username", snow_username)
        self.settings.setValue("snow_password", snow_password)
        if self.debug_checkbox.isChecked():
            self.settings.setValue("debug", 1)
            debug=True
        else:
            self.settings.setValue("debug", 0)
            debug=False
        self.settings.sync()


class snowWorker(QRunnable):

    def setMainWindow(self, MainWindow):
        self.MainWindow = MainWindow
        self.refresh=False

    def setRefresh(self, refresh):
        self.refresh=refresh

    def getUnattendedIncidentCount(self):
        global snow_instance, snow_username, snow_password
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

        return len(response.all())

    @pyqtSlot()
    def run(self):
        global debug
        self.refresh=False

        if debug:
            print("running fetch_incident_count")

        while True:
            if debug:
                print("checking incidents...")

            incident_count=self.getUnattendedIncidentCount()

            if incident_count==0:
                self.MainWindow.tray_icon.setIcon(self.MainWindow.style().standardIcon(QStyle.SP_DialogApplyButton))
            else:
                self.MainWindow.tray_icon.setIcon(self.MainWindow.style().standardIcon(QStyle.SP_MessageBoxCritical))
                self.MainWindow.tray_icon.showMessage(
                "Unattended INCIDENTS",
                "Incident count: "+str(incident_count),
                QSystemTrayIcon.Critical,
                msecs=10000
                )
            self.MainWindow.tray_icon.show()
            if debug:
                print("Sleeping 60 seconds")
            for i in range(60):
                if self.refresh:
                    self.refresh=False
                    break
                else:
                    time.sleep(1)

class MainWindow(QMainWindow):
    check_box = None
    tray_icon = None

    def refresh_unattended_incidents(self):
        self.snow_worker.setRefresh(True)

    # Override the class constructor
    def __init__(self):
        # Be sure to call the super class method
        QMainWindow.__init__(self)
        self.threadpool = QThreadPool()
        self.snow_worker = snowWorker()
        self.snow_worker.setMainWindow(self)

        self.setMinimumSize(QSize(480, 80))             # Set sizes
        self.setWindowTitle("gatekeeper Desktop")  # Set a title
        central_widget = QWidget(self)                  # Create a central widget
        self.setCentralWidget(central_widget)           # Set the central widget

        grid_layout = QGridLayout(self)         # Create a QGridLayout
        central_widget.setLayout(grid_layout)   # Set the layout into the central widget
        grid_layout.addWidget(QLabel("gatekeeper Desktop settings", self), 0, 0)

        self.alert_on_unattended_incidents = QCheckBox('check unattended incidents')
        self.alert_on_unattended_incidents.setChecked(1)
        grid_layout.addWidget(self.alert_on_unattended_incidents, 1, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)

        self.alert_on_assigned_incidents = QCheckBox('check assigned incidents')
        self.alert_on_assigned_incidents.setChecked(1)
        grid_layout.addWidget(self.alert_on_assigned_incidents, 2, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)

        # Init QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))

        refresh_action = QAction("Refresh", self)
        show_action = QAction("Show", self)
        hide_action = QAction("Hide", self)
        quit_action = QAction("Exit", self)

        refresh_action.triggered.connect(self.refresh_unattended_incidents)
        show_action.triggered.connect(self.show)
        hide_action.triggered.connect(self.hide)
        quit_action.triggered.connect(qApp.quit)

        tray_menu = QMenu(parent=None)
        tray_menu.aboutToShow.connect(self.refresh_unattended_incidents)
        tray_menu.addAction(refresh_action)
        tray_menu.addAction(show_action)
        tray_menu.addAction(hide_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # run bg job
        self.threadpool.start(self.snow_worker)


    # Override closeEvent, to intercept the window closing event
    # The window will be closed only if there is no check mark in the check box
    def closeEvent(self, event):
        event.ignore()
        self.hide()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    login = Login()

    if login.exec_() == QtWidgets.QDialog.Accepted:
        main_window = MainWindow()
        sys.exit(app.exec())
