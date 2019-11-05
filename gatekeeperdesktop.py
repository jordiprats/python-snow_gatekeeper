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
snow_team = ""
display_name = ""
debug = 0
window_mode = False
main_window = None

check_unattended_incidents = True
check_assigned_incidents = True

class Login(QtWidgets.QDialog):
    def __init__(self, parent=None):
        global snow_instance, snow_username, snow_password, debug, check_unattended_incidents, check_assigned_incidents, window_mode
        super(Login, self).__init__(parent)

        self.setWindowTitle("Login")
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))

        self.settings = QtCore.QSettings()

        self.textInstance = QtWidgets.QLineEdit(self)
        self.textName = QtWidgets.QLineEdit(self)
        self.textPass = QtWidgets.QLineEdit(self)
        self.textPass.setEchoMode(QtWidgets.QLineEdit.Password)
        self.textTeam = QtWidgets.QLineEdit(self)

        self.textInstance.setText(self.settings.value("snow_instance"))
        self.textName.setText(self.settings.value("snow_username"))
        self.textPass.setText(self.settings.value("snow_password"))
        self.textTeam.setText(self.settings.value("snow_team"))

        self.debug_checkbox = QCheckBox('debug')
        if self.settings.value("debug") == '1':
            self.debug_checkbox.setChecked(1)
            debug=True
        else:
            self.debug_checkbox.setChecked(0)
            debug=False

        self.windowmode_checkbox = QCheckBox('window mode')
        if self.settings.value("window_mode") == '1':
            self.windowmode_checkbox.setChecked(1)
            debug=True
        else:
            self.windowmode_checkbox.setChecked(0)
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
        layout.addWidget(QLabel("team:", self))
        layout.addWidget(self.textTeam)
        layout.addWidget(QLabel("options:", self))
        layout.addWidget(self.debug_checkbox)
        layout.addWidget(self.windowmode_checkbox)

        layout.addWidget(self.buttonLogin)

        if self.settings.value("check_unattended_incidents") == '1':
            check_unattended_incidents=True
        else:
            check_unattended_incidents=False
        if self.settings.value("check_assigned_incidents") == '1':
            check_assigned_incidents=True
        else:
            check_assigned_incidents=False

    def handleLogin(self):
        global snow_instance, snow_username, snow_password, snow_team, debug, display_name, window_mode
        snow_instance = self.textInstance.text()
        snow_username = self.textName.text()
        snow_password = self.textPass.text()
        snow_team = self.textTeam.text()

        try:
            client = pysnow.Client(instance=snow_instance, user=snow_username, password=snow_password)
            response = (client
                .resource(api_path='/table/sys_user')
                .get(query={'user_name': snow_username})
                .one())
            display_name = response['name']
            self.accept()

        except Exception as e:
            QtWidgets.QMessageBox.warning(
                self, 'Error', 'Bad user or password: '+str(e))

        self.settings.setValue("snow_instance", snow_instance)
        self.settings.setValue("snow_username", snow_username)
        self.settings.setValue("snow_password", snow_password)
        self.settings.setValue("snow_team", snow_team)
        if self.debug_checkbox.isChecked():
            self.settings.setValue("debug", '1')
            debug=True
        else:
            self.settings.setValue("debug", '0')
            debug=False
        if self.windowmode_checkbox.isChecked():
            self.settings.setValue("window_mode", '1')
            window_mode=True
        else:
            self.settings.setValue("window_mode", '0')
            window_mode=False

        if not settings.value("check_unattended_incidents"):
            self.settings.setValue("check_unattended_incidents", '1')
        if not settings.value("check_assigned_incidents"):
            self.settings.setValue("check_assigned_incidents", '1')

        self.settings.sync()


class snowWorker(QRunnable):

    def setMainWindow(self, MainWindow):
        self.MainWindow = MainWindow
        self.refresh=False

    def setRefresh(self, refresh):
        self.refresh=refresh

    def getAssignedIncidentCount(self):
        global snow_instance, snow_username, snow_password, snow_team, debug, display_name
        print("    def getAssignedIncidentCount(self):")
        c = pysnow.client.Client(instance=snow_instance, user=snow_username, password=snow_password)

        qb = (pysnow.QueryBuilder()
                .field('assigned_to.name').equals(display_name)
                .AND()
                .field('active').equals('true')
                .AND()
                .field('state').equals('2') # work in progress
                )

        incident = c.resource(api_path='/table/incident')
        response = incident.get(query=qb)

        if debug:
            for record in response.all():
                print(record['number'])

        count=len(response.all())
        if debug:
            print("    "+str(count))
        return count

    def getUnattendedIncidentCount(self):
        global snow_instance, snow_username, snow_password, snow_team, debug
        print("    def getUnattendedIncidentCount(self):")
        c = pysnow.client.Client(instance=snow_instance, user=snow_username, password=snow_password)

        qb = (pysnow.QueryBuilder()
                .field('assigned_to').is_empty()
                .AND()
                .field('assignment_group.name').equals(snow_team)
                .AND()
                .field('active').equals('true')
                .AND()
                .field('state').not_equals('6') # not resolved
                )

        incident = c.resource(api_path='/table/incident')
        response = incident.get(query=qb)

        if debug:
            for record in response.all():
                print(record['number'])

        count=len(response.all())
        if debug:
            print("    "+str(count))
        return count

    @pyqtSlot()
    def run(self):
        global debug
        self.refresh=False

        settings = QtCore.QSettings()

        if debug:
            print("running fetch_incident_count")

        previous_unattended_incident_count=0
        previous_user_assigned_incident_count=0
        while True:
            try:
                settings.sync()
                if debug:
                    print("checking incidents...")

                if debug:
                    print("settings::check_unattended_incidents: "+str(settings.value("check_unattended_incidents")))
                if settings.value("check_unattended_incidents") == '0':
                    check_unattended_incidents=False
                else:
                    check_unattended_incidents=True

                if debug:
                    print("settings::check_assigned_incidents: "+str(settings.value("check_assigned_incidents")))
                if settings.value("check_assigned_incidents") == '0':
                    check_assigned_incidents=False
                else:
                    check_assigned_incidents=True

                if check_unattended_incidents:
                    unattended_incident_count=self.getUnattendedIncidentCount()
                else:
                    unattended_incident_count=0

                if check_assigned_incidents:
                    user_assigned_incident_count=self.getAssignedIncidentCount()
                else:
                    user_assigned_incident_count=0

                if unattended_incident_count==0:
                    if user_assigned_incident_count==0:
                        self.MainWindow.tray_icon.setIcon(self.MainWindow.style().standardIcon(QStyle.SP_DialogApplyButton))
                    else:
                        self.MainWindow.tray_icon.setIcon(self.MainWindow.style().standardIcon(QStyle.SP_MessageBoxWarning))
                        if previous_user_assigned_incident_count!=user_assigned_incident_count:
                            previous_user_assigned_incident_count=user_assigned_incident_count
                            previous_unattended_incident_count=0
                            if not QSystemTrayIcon.isSystemTrayAvailable():
                                import notify2
                                notify2.init("gatekeeper Desktop")
                                n = notify2.Notification("ASSIGNED INCIDENTS", "Assigned incident count: "+str(user_assigned_incident_count))
                                n.set_urgency(notify2.URGENCY_NORMAL)
                                n.show()
                            else:
                                self.MainWindow.tray_icon.showMessage(
                                    "ASSIGNED INCIDENTS",
                                    "Assigned incident count: "+str(user_assigned_incident_count),
                                    QSystemTrayIcon.Warning,
                                    msecs=10000
                                )
                else:
                    self.MainWindow.tray_icon.setIcon(self.MainWindow.style().standardIcon(QStyle.SP_MessageBoxCritical))
                    if previous_unattended_incident_count!=unattended_incident_count:
                        previous_unattended_incident_count=unattended_incident_count
                        previous_user_assigned_incident_count=0
                        if not QSystemTrayIcon.isSystemTrayAvailable():
                            import notify2
                            notify2.init("gatekeeper Desktop")
                            n = notify2.Notification("Unattended INCIDENTS", "Incident count: "+str(unattended_incident_count))
                            n.set_urgency(notify2.URGENCY_NORMAL)
                            n.show()
                        else:
                            self.MainWindow.tray_icon.showMessage(
                                "Unattended INCIDENTS",
                                "Incident count: "+str(unattended_incident_count),
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
            except Exception as e:
                print("Exception snowWorker::run: "+str(e))

class MainWindow(QMainWindow):
    check_box = None
    tray_icon = None

    def refresh_unattended_incidents(self):
        self.snow_worker.setRefresh(True)

    # Override the class constructor
    def __init__(self):
        global check_unattended_incidents, check_assigned_incidents
        # Be sure to call the super class method
        self.settings = QtCore.QSettings()
        QMainWindow.__init__(self)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
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
        if check_unattended_incidents:
            self.alert_on_unattended_incidents.setChecked(1)
        else:
            self.alert_on_unattended_incidents.setChecked(0)
        grid_layout.addWidget(self.alert_on_unattended_incidents, 1, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)

        self.alert_on_assigned_incidents = QCheckBox('check assigned incidents')
        if check_assigned_incidents:
            self.alert_on_assigned_incidents.setChecked(1)
        else:
            self.alert_on_assigned_incidents.setChecked(0)
        grid_layout.addWidget(self.alert_on_assigned_incidents, 2, 0)
        grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 2, 0)

        # Init QSystemTrayIcon
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_BrowserReload))
        self.tray_icon.setVisible(True)

        refresh_action = QAction("Refresh", self)
        show_action = QAction("Show", self)
        quit_action = QAction("Exit", self)

        refresh_action.triggered.connect(self.refresh_unattended_incidents)
        show_action.triggered.connect(self.show)
        quit_action.triggered.connect(qApp.quit)

        tray_menu = QMenu(parent=None)
        tray_menu.aboutToShow.connect(self.refresh_unattended_incidents)
        tray_menu.addAction(refresh_action)
        tray_menu.addAction(show_action)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # run bg job
        self.threadpool.start(self.snow_worker)


    # Override closeEvent, to intercept the window closing event
    # The window will be closed only if there is no check mark in the check box
    def closeEvent(self, event):

        if self.alert_on_unattended_incidents.isChecked():
            self.settings.setValue("check_unattended_incidents", '1')
        else:
            self.settings.setValue("check_unattended_incidents", '0')

        if self.alert_on_assigned_incidents.isChecked():
            self.settings.setValue("check_assigned_incidents", '1')
        else:
            self.settings.setValue("check_assigned_incidents", '0')

        self.settings.sync()
        event.ignore()
        self.hide()

if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    login = Login()

    if login.exec_() == QtWidgets.QDialog.Accepted:
        main_window = MainWindow()
        sys.exit(app.exec())
