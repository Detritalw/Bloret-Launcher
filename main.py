import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QLabel
from qfluentwidgets import NavigationInterface, NavigationItemPosition
import datetime
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QDesktopServices
from PyQt5.QtCore import QPropertyAnimation, QRect, QEasingCurve, QUrl
import requests
import base64
import json

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bloret 启动器 (beta)")
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon("icons/bloret.png"))  # 设置软件图标

        self.player_uuid = ""  # Initialize player_uuid

        # 创建侧边栏
        self.navigation_interface = NavigationInterface(self)
        self.navigation_interface.addItem(
            routeKey="home",
            icon="icons/bloret.png",
            text="主页",
            onClick=self.on_home_clicked,
            position=NavigationItemPosition.TOP
        )
        self.navigation_interface.addItem(
            routeKey="download",
            icon="icons/download.png",
            text="下载",
            onClick=self.on_download_clicked,
            position=NavigationItemPosition.TOP
        )
        self.navigation_interface.addItem(
            routeKey="tools",
            icon="icons/tools.png",
            text="工具",
            onClick=self.on_tools_clicked,
            position=NavigationItemPosition.TOP
        )
        self.navigation_interface.addItem(
            routeKey="passport",
            icon="icons/passport.png",
            text="通行证",
            onClick=self.on_passport_clicked,
            position=NavigationItemPosition.BOTTOM
        )
        self.navigation_interface.addItem(
            routeKey="settings",
            icon="icons/settings.png",
            text="设置",
            onClick=self.on_settings_clicked,
            position=NavigationItemPosition.BOTTOM
        )
        self.navigation_interface.addItem(
            routeKey="info",
            icon="icons/info.png",
            text="关于",
            onClick=self.on_info_clicked,
            position=NavigationItemPosition.BOTTOM
        )

        # 创建按钮
        self.button = QPushButton("Click Me")
        self.button.clicked.connect(self.on_button_clicked)

        # 主布局
        self.main_layout = QHBoxLayout()  # 使用QHBoxLayout使侧边栏在左侧，内容在右侧
        self.main_layout.addWidget(self.navigation_interface)

        self.content_layout = QVBoxLayout()
        self.content_layout.addWidget(self.button)
        self.main_layout.addLayout(self.content_layout)

        self.container = QWidget()
        self.container.setLayout(self.main_layout)
        self.setCentralWidget(self.container)

        self.animation_duration = 300  # 动画持续时间（毫秒）

        # 创建侧边栏动画
        self.sidebar_animation = QPropertyAnimation(self.navigation_interface, b"geometry")
        self.sidebar_animation.setDuration(self.animation_duration)
        self.sidebar_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # 创建内容淡入动画
        self.fade_in_animation = QPropertyAnimation(self.container, b"windowOpacity")
        self.fade_in_animation.setDuration(self.animation_duration)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # 默认加载主页
        self.load_ui("ui/home.ui", animate=False)

    def on_home_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 主页 被点击")
        self.load_ui("ui/home.ui")

    def on_download_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 下载 被点击")
        self.load_ui("ui/download.ui")

    def on_passport_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 通行证 被点击")
        self.load_ui("ui/passport.ui")

    def on_settings_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 设置 被点击")
        self.load_ui("ui/settings.ui")

    def on_info_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 关于 被点击")
        self.load_ui("ui/info.ui")

    def on_tools_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 工具 被点击")
        self.load_ui("ui/tools.ui")

    def load_ui(self, ui_path, animate=True):
        widget = uic.loadUi(ui_path)
        # 清除之前的内容
        for i in reversed(range(self.content_layout.count())):
            self.content_layout.itemAt(i).widget().setParent(None)
        self.content_layout.addWidget(widget)

        if ui_path == "ui/home.ui":
            github_org_button = widget.findChild(QPushButton, "pushButton_2")
            if github_org_button:
                github_org_button.clicked.connect(self.open_github_bloret)
            github_project_button = widget.findChild(QPushButton, "pushButton")
            if github_project_button:
                github_project_button.clicked.connect(self.open_github_bloret_Launcher)

        elif ui_path == "ui/info.ui":
            github_org_button = widget.findChild(QPushButton, "pushButton_2")
            if github_org_button:
                github_org_button.clicked.connect(self.open_github_bloret)
            github_project_button = widget.findChild(QPushButton, "button_github")
            if github_project_button:
                github_project_button.clicked.connect(self.open_github_bloret_Launcher)

        elif ui_path == "ui/tools.ui":
            query_button = widget.findChild(QPushButton, "name2uuid_player_Button")
            if query_button:
                query_button.clicked.connect(lambda: self.query_player_uuid(widget))
            copy_button = widget.findChild(QPushButton, "pushButton_5")
            if copy_button:
                copy_button.clicked.connect(lambda: self.copy_to_clipboard(widget))
            skin_search_button = widget.findChild(QPushButton, "skin_search_button")
            if skin_search_button:
                skin_search_button.clicked.connect(lambda: self.query_player_skin(widget))
            skin_copy_button = widget.findChild(QPushButton, "search_skin_copy")
            if skin_copy_button:
                skin_copy_button.clicked.connect(lambda: self.copy_skin_to_clipboard(widget))
            skin_down_button = widget.findChild(QPushButton, "search_skin_down")
            if skin_down_button:
                skin_down_button.clicked.connect(lambda: self.open_skin_url(widget))
            cape_copy_button = widget.findChild(QPushButton, "search_cape_copy")
            if cape_copy_button:
                cape_copy_button.clicked.connect(lambda: self.copy_cape_to_clipboard(widget))
            cape_down_button = widget.findChild(QPushButton, "search_cape_down")
            if cape_down_button:
                cape_down_button.clicked.connect(lambda: self.open_cape_url(widget))

        if animate:
            self.animate_sidebar()
            self.animate_fade_in()

    def query_player_uuid(self, widget):
        player_name_edit = widget.findChild(QLineEdit, "name2uuid_player_uuid")
        result_label = widget.findChild(QLabel, "label_2")
        if player_name_edit and result_label:
            result_label.setText("查询中，请稍等...")
            player_name = player_name_edit.text()
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}")
            if response.status_code == 200:
                player_data = response.json()
                self.player_uuid = player_data.get("id", "未找到UUID")
                self.player_name = player_name  # Store player name for later use
                result_label.setText(self.player_uuid)
            else:
                result_label.setText("查询失败")

    def copy_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_uuid)

    def query_player_skin(self, widget):
        player_uuid_edit = widget.findChild(QLineEdit, "skin_uuid")
        skin_result_label = widget.findChild(QLabel, "search_skin")
        cape_result_label = widget.findChild(QLabel, "search_cape")
        if player_uuid_edit and skin_result_label and cape_result_label:
            skin_result_label.setText("查询中，请稍等...")
            cape_result_label.setText("查询中，请稍等...")
            player_uuid = player_uuid_edit.text()
            response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{player_uuid}")
            if response.status_code == 200:
                player_data = response.json()
                properties = player_data.get("properties", [])
                if properties:
                    value = properties[0].get("value", "")
                    decoded_data = base64.b64decode(value).decode('utf-8')
                    textures = json.loads(decoded_data).get("textures", {})
                    self.player_skin = textures.get("SKIN", {}).get("url", "未找到皮肤URL")
                    self.player_cape = textures.get("CAPE", {}).get("url", "未找到披风URL")
                    skin_result_label.setText(self.player_skin[:20] + "..." if len(self.player_skin) > 20 else self.player_skin)
                    cape_result_label.setText(self.player_cape[:20] + "..." if len(self.player_cape) > 20 else self.player_cape)
                    print(f"{datetime.datetime.now()} [INFO] 皮肤URL: {self.player_skin}")
                    print(f"{datetime.datetime.now()} [INFO] 披风URL: {self.player_cape}")
                else:
                    skin_result_label.setText("未找到皮肤信息")
                    cape_result_label.setText("未找到披风信息")
            else:
                skin_result_label.setText("查询失败")
                cape_result_label.setText("查询失败")

    def copy_skin_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_skin)

    def copy_cape_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_cape)

    def open_skin_url(self, widget):
        QDesktopServices.openUrl(QUrl(self.player_skin))

    def open_cape_url(self, widget):
        QDesktopServices.openUrl(QUrl(self.player_cape))

    def open_github_bloret(self):
        QDesktopServices.openUrl(QUrl("https://github.com/BloretCrew"))

    def open_github_bloret_Launcher(self):
        QDesktopServices.openUrl(QUrl("https://github.com/BloretCrew/Bloret-Launcher"))

    def animate_sidebar(self):
        start_geometry = self.navigation_interface.geometry()
        end_geometry = QRect(start_geometry.x(), start_geometry.y(), start_geometry.width(), start_geometry.height())
        self.sidebar_animation.setStartValue(start_geometry)
        self.sidebar_animation.setEndValue(end_geometry)
        self.sidebar_animation.start()

    def animate_fade_in(self):
        self.fade_in_animation.start()

    def on_button_clicked(self):
        print(f"{datetime.datetime.now()} [INFO] 按钮 被点击")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
