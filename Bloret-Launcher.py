from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLineEdit, QLabel, QFileDialog, QCheckBox, QMessageBox
from qfluentwidgets import NavigationInterface, NavigationItemPosition, TeachingTip, InfoBarIcon, TeachingTipTailPosition, ComboBox, SwitchButton, InfoBar, ProgressBar, InfoBarPosition, FluentWindow
from PyQt5 import uic
from PyQt5.QtGui import QIcon, QDesktopServices, QCursor, QColor, QPalette, QMovie, QPixmap
from PyQt5.QtCore import QPropertyAnimation, QRect, QEasingCurve, QUrl, QSettings, QThread, pyqtSignal, Qt, QTimer
from win10toast import ToastNotifier
import sys
import logging
import os
import requests
import base64
import json
import configparser
import subprocess
import sip # type: ignore
import zipfile
import time
import shutil
from win32com.client import Dispatch
import platform
# 全局变量
ver_id_bloret = ['1.21.4', '1.21.3', '1.21.2', '1.21.1', '1.21']
ver_id_main = []
ver_id_short = []
ver_id = [] 
ver_url = {}
ver_id_long = []
set_list = ["你还未安装任何版本哦，请前往下载页面安装"]

# 创建日志文件夹
if not os.path.exists('log'):
    os.makedirs('log')
# 设置日志配置
log_filename = os.path.join('log', f'log_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(filename=log_filename, level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
class DownloadWorker(QThread):
    finished = pyqtSignal()
    def run(self):
        # 模拟数据处理
        import time
        time.sleep(5)  # 模拟数据处理耗时
        self.finished.emit()
class RunScriptThread(QThread):
    finished = pyqtSignal()
    error_occurred = pyqtSignal(str)
    output_received = pyqtSignal(str)
    last_output_received = pyqtSignal(str)  # 新增信号
    def run(self):
        script_path = "run.ps1"
        try:
            process = subprocess.Popen(
                ["powershell", "-ExecutionPolicy", "Bypass", "-File", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='latin-1',
                errors='ignore'
            )
            last_line = ""
            for line in iter(process.stdout.readline, ''):
                last_line = line.strip()
                self.output_received.emit(last_line)
            self.last_output_received.emit(last_line)  # 发射最后一行输出信号
            process.stdout.close()
            process.wait()
            if process.returncode == 0:
                self.finished.emit()
            else:
                self.error_occurred.emit(process.stderr.read().strip())
        except subprocess.CalledProcessError as e:
            self.error_occurred.emit(str(e.stderr))
class UpdateShowTextThread(QThread):
    update_text = pyqtSignal(str)
    def __init__(self, run_script_thread):
        super().__init__()
        self.run_script_thread = run_script_thread
        self.last_output = ""
    def run(self):
        while self.run_script_thread.isRunning():
            time.sleep(1)  # 每秒更新一次
            self.update_text.emit(self.last_output)
    def update_last_output(self, text):
        self.last_output = text
class LoadMinecraftVersionsThread(QThread):
    versions_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    def __init__(self, version_type):
        super().__init__()
        self.version_type = version_type
    def run(self):
        try:
            response = requests.get("https://bmclapi2.bangbang93.com/mc/game/version_manifest.json")
            response.raise_for_status()
            version_data = response.json()
            versions = version_data["versions"]
            ver_id_main.clear()
            ver_id_short.clear()
            ver_id_long.clear()
            for version in versions:
                if version["type"] not in ["snapshot", "old_alpha", "old_beta"]:
                    ver_id_main.append(version["id"])
                else:
                    if version["type"] == "snapshot":
                        ver_id_short.append(version["id"])
                    elif version["type"] in ["old_alpha", "old_beta"]:
                        ver_id_long.append(version["id"])
            if self.version_type == "百络谷支持版本":
                self.versions_loaded.emit(ver_id_bloret)
            elif self.version_type == "正式版本":
                self.versions_loaded.emit(ver_id_main)
            elif self.version_type == "快照版本":
                self.versions_loaded.emit(ver_id_short)
            elif self.version_type == "远古版本":
                self.versions_loaded.emit(ver_id_long)
            else:
                self.error_occurred.emit("未知的版本类型")
        except requests.RequestException as e:
            self.error_occurred.emit(f"请求错误: {e}")
        except requests.exceptions.SSLError as e:
            self.error_occurred.emit(f"SSL 错误: {e}")
class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        # 初始化 sidebar_animation
        self.sidebar_animation = QPropertyAnimation(self.navigationInterface, b"geometry")
        self.sidebar_animation.setDuration(300)  # 设置动画持续时间
        self.sidebar_animation.setEasingCurve(QEasingCurve.InOutQuad)
        # 初始化 fade_in_animation
        self.fade_in_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_in_animation.setDuration(500)
        self.fade_in_animation.setStartValue(0)
        self.fade_in_animation.setEndValue(1)
        self.fade_in_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.loading_dialogs = []  # 初始化 loading_dialogs 属性
        self.threads = []  # 初始化 threads 属性
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.logshow = self.config.getboolean('DEFAULT', 'logshow', fallback=False)
        self.handle_first_run()
        self.logshow = self.config.getboolean('DEFAULT', 'logshow', fallback=False)
        self.check_for_updates()
        self.setWindowTitle("Bloret 启动器 (Preview)")  # 设置软件标题
        self.setGeometry(100, 100, 800, 600)
        self.setWindowIcon(QIcon("icons/bloret.png"))  # 设置软件图标
        self.is_running = False
        self.player_uuid = ""  
        self.player_skin = ""  
        self.player_cape = ""  
        self.player_name = ""  
        self.settings = QSettings("Bloret", "Launcher")
        self.apply_theme()
        self.initNavigation()
        self.initWindow()
        self.show()
        self.setAttribute(Qt.WA_QuitOnClose, True)  # 确保窗口关闭时程序退出
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)  # 确保窗口显示在最前面
        self.raise_()
        self.activateWindow()
    def initNavigation(self):
        self.homeInterface = QWidget()
        self.downloadInterface = QWidget()
        self.toolsInterface = QWidget()
        self.passportInterface = QWidget()
        self.settingsInterface = QWidget()
        self.infoInterface = QWidget()
        self.homeInterface.setObjectName("home")
        self.downloadInterface.setObjectName("download")
        self.toolsInterface.setObjectName("tools")
        self.passportInterface.setObjectName("passport")
        self.settingsInterface.setObjectName("settings")
        self.infoInterface.setObjectName("info")
        self.addSubInterface(self.homeInterface, QIcon("icons/bloret.png"), "主页")
        self.addSubInterface(self.downloadInterface, QIcon("icons/download.png"), "下载")
        self.addSubInterface(self.toolsInterface, QIcon("icons/tools.png"), "工具")
        self.addSubInterface(self.passportInterface, QIcon("icons/passport.png"), "通行证", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.settingsInterface, QIcon("icons/settings.png"), "设置", NavigationItemPosition.BOTTOM)
        self.addSubInterface(self.infoInterface, QIcon("icons/info.png"), "关于", NavigationItemPosition.BOTTOM)
        self.load_ui("ui/home.ui", parent=self.homeInterface)
        self.load_ui("ui/download.ui", parent=self.downloadInterface)
        self.load_ui("ui/tools.ui", parent=self.toolsInterface)
        self.load_ui("ui/passport.ui", parent=self.passportInterface)
        self.load_ui("ui/settings.ui", parent=self.settingsInterface)
        self.load_ui("ui/info.ui", parent=self.infoInterface)
    def animate_sidebar(self):
        start_geometry = self.navigationInterface.geometry()
        end_geometry = QRect(start_geometry.x(), start_geometry.y(), start_geometry.width(), start_geometry.height())
        self.sidebar_animation.setStartValue(start_geometry)
        self.sidebar_animation.setEndValue(end_geometry)
        self.sidebar_animation.start()
    def initWindow(self):
        self.resize(900, 700)
        self.setWindowIcon(QIcon("icons/bloret.png"))
        self.setWindowTitle("Bloret 启动器 (Preview)")
    def load_ui(self, ui_path, parent=None, animate=True):
        widget = uic.loadUi(ui_path)
        
        if parent:
            # 确保父部件只有一个布局
            if parent.layout() is None:
                parent.setLayout(QVBoxLayout())
            parent.layout().addWidget(widget)  # 直接添加到现有布局
        
        if animate:
            self.animate_sidebar()
            self.animate_fade_in()
    def on_home_clicked(self):
        self.log("主页 被点击")
        self.switchTo(self.homeInterface)
    def on_download_clicked(self):
        self.log("下载 被点击")
        self.switchTo(self.downloadInterface)
    def on_tools_clicked(self):
        self.log("工具 被点击")
        self.switchTo(self.toolsInterface)
    def on_passport_clicked(self):
        self.log("通行证 被点击")
        self.switchTo(self.passportInterface)
    def on_settings_clicked(self):
        self.log("设置 被点击")
        self.switchTo(self.settingsInterface)
    def on_info_clicked(self):
        self.log("关于 被点击")
        self.switchTo(self.infoInterface)
    def run_cmcl_list(self):
        try:
            result = subprocess.run(
                ["cmcl.exe", "-l"],
                capture_output=True,
                text=True,
                check=True,
                encoding="utf-8"  # 明确指定编码
            )
            # 按空格分割并过滤空字符串
            cmcl_output_list = result.stdout.strip().replace("\r", "").split()
            global set_list
            set_list = cmcl_output_list if cmcl_output_list else ["你还未安装任何版本"]
        except Exception as e:
            self.log(f"运行 cmcl -l 失败: {e}", logging.ERROR)
            set_list = ["无法获取版本列表"]
    def log(self, message, level=logging.INFO):
        if self.logshow:
            print(message)
        else:
            logging.log(level, message)
    def closeEvent(self, event):
        for thread in self.threads:
            if thread.isRunning():
                thread.terminate()
                thread.wait()
        event.accept()
    def on_download_clicked(self):
        self.log("下载 被点击")
        self.load_ui("ui/download.ui", animate=False)
        self.setup_download_ui(self.content_layout.itemAt(0).widget())
    def setup_download_ui(self, widget):
        minecraft_part_edit = widget.findChild(QLineEdit, "minecraft_part")
        minecraft_part_choose_button = widget.findChild(QPushButton, "minecraft_part_choose")
        minecraft_part_set_button = widget.findChild(QPushButton, "minecraft_part_set")
        download_way_choose = widget.findChild(ComboBox, "download_way_choose")  # 获取 download_way_choose 元素
        download_way_F5_button = widget.findChild(QPushButton, "download_way_F5")
        minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
        show_way = widget.findChild(ComboBox, "show_way")
        download_button = widget.findChild(QPushButton, "download")
        if minecraft_part_edit:
            config = configparser.ConfigParser()
            config.read('config.ini')
            if 'DEFAULT' in config and 'minecraft-part' in config['DEFAULT']:
                minecraft_part_edit.setText(config['DEFAULT']['minecraft-part'])
            else:
                minecraft_part_edit.setText(os.path.join(os.getcwd(), ".minecraft"))
        if minecraft_part_choose_button:
            minecraft_part_choose_button.clicked.connect(lambda: self.choose_minecraft_part(widget))
        if minecraft_part_set_button:
            minecraft_part_set_button.clicked.connect(lambda: self.set_minecraft_part(widget))
        if show_way:
            show_way.clear()
            show_way.addItems(["百络谷支持版本", "正式版本", "快照版本", "远古版本"])
            show_way.setCurrentText("百络谷支持版本")
            show_way.currentTextChanged.connect(lambda: self.on_show_way_changed(widget, show_way.currentText()))
        if download_way_choose:
            download_way_choose.clear()  # 清空下拉框
            download_way_choose.addItem("BMCLAPI")  # 只添加 BMCLAPI
        if download_way_F5_button:
            download_way_F5_button.clicked.connect(lambda: self.update_minecraft_versions(widget, show_way.currentText()))
        if download_button:
            download_button.clicked.connect(lambda: self.start_download(widget))
        loading_label = widget.findChild(QLabel, "label_2")
        if loading_label:
            self.setup_loading_gif(loading_label)
        # 默认填入百络谷支持版本
        if minecraft_choose:
            minecraft_choose.clear()
            minecraft_choose.addItems(ver_id_bloret)
        notification_switch = widget.findChild(SwitchButton, "Notification")
        if notification_switch:
            notification_switch.setChecked(True)  # 将Notification开关设置成开
    def on_show_way_changed(self, widget, version_type):
        show_way = widget.findChild(ComboBox, "show_way")
        minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")

        if show_way and minecraft_choose:
            show_way.setEnabled(False)
            minecraft_choose.setEnabled(False)
            InfoBar.success(
                title='⏱️ 正在加载',
                content=f"正在加载 {version_type} 的列表",
                orient=Qt.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP,
                duration=3000,
                parent=self
            )
        def fetch_versions():
            self.load_versions_thread = LoadMinecraftVersionsThread(version_type)
            self.threads.append(self.load_versions_thread)  # 将线程添加到列表中
            self.load_versions_thread.versions_loaded.connect(lambda versions: self.update_minecraft_choose(widget, versions))
            self.load_versions_thread.error_occurred.connect(lambda error: self.show_error_tip(widget, error))
            self.load_versions_thread.start()
        QTimer.singleShot(2000, fetch_versions)
    def update_minecraft_choose(self, widget, versions):
        minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
        show_way = widget.findChild(ComboBox, "show_way")
        if minecraft_choose:
            minecraft_choose.clear()
            minecraft_choose.addItems(versions)
            minecraft_choose.setEnabled(True)
        if show_way:
            show_way.setEnabled(True)
        for dialog in self.loading_dialogs:
            dialog.close()
        self.loading_dialogs.clear()
    def show_error_tip(self, widget, error):
        show_way = widget.findChild(ComboBox, "show_way")
        minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
        if show_way:
            show_way.setEnabled(True)
        if minecraft_choose:
            minecraft_choose.setEnabled(True)
        TeachingTip.create(
            target=widget,
            icon=InfoBarIcon.ERROR,
            title='错误',
            content=f"加载列表时出错: {error}",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=2000,
            parent=self
        )
        for dialog in self.loading_dialogs:
            dialog.close()
        self.loading_dialogs.clear()
    def choose_minecraft_part(self, widget):
        minecraft_part_edit = widget.findChild(QLineEdit, "minecraft_part")
        minecraft_part_choose_button = widget.findChild(QPushButton, "minecraft_part_choose")
        if minecraft_part_edit and minecraft_part_choose_button:
            folder_path = QFileDialog.getExistingDirectory(self, "选择 .minecraft 文件夹", os.getcwd())
            if folder_path:
                minecraft_part_edit.setText(folder_path)
                config = configparser.ConfigParser()
                config.read('config.ini')
                if 'DEFAULT' not in config:
                    config['DEFAULT'] = {}
                config['DEFAULT']['minecraft-part'] = folder_path
                with open('config.ini', 'w') as configfile:
                    config.write(configfile)
                self.log(f"选择的 .minecraft 文件夹路径: {folder_path}")
                self.showTeachingTip(minecraft_part_choose_button, folder_path)
    def set_minecraft_part(self, widget):
        minecraft_part_edit = widget.findChild(QLineEdit, "minecraft_part")
        minecraft_part_set_button = widget.findChild(QPushButton, "minecraft_part_set")
        if minecraft_part_edit and minecraft_part_set_button:
            folder_path = minecraft_part_edit.text()
            config = configparser.ConfigParser()
            config.read('config.ini')
            if 'DEFAULT' not in config:
                config['DEFAULT'] = {}
            config['DEFAULT']['minecraft-part'] = folder_path
            with open('config.ini', 'w') as configfile:
                config.write(configfile)
            self.log(f"设置的 .minecraft 文件夹路径: {folder_path}")
            self.showTeachingTip(minecraft_part_set_button, folder_path)
    def showTeachingTip(self, target_widget, folder_path):
        if sip.isdeleted(target_widget):
            self.log(f"目标小部件已被删除，无法显示 TeachingTip", logging.ERROR)
            return
        TeachingTip.create(
            target=target_widget,
            icon=InfoBarIcon.SUCCESS,
            title='提示',
            content=f"已存储 Minecraft 核心文件夹位置为\n{folder_path}",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=2000,
            parent=self
        ).move(target_widget.mapToGlobal(target_widget.rect().topLeft()))
    def update_minecraft_versions(self, widget, version_type):
        minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
        if minecraft_choose:
            try:
                response = requests.get("https://bmclapi2.bangbang93.com/mc/game/version_manifest.json")
                if response.status_code == 200:
                    version_data = response.json()
                    latest_release = version_data["latest"]["release"]
                    latest_snapshot = version_data["latest"]["snapshot"]
                    versions = version_data["versions"]
                    ver_id_main.clear()
                    ver_id_short.clear()
                    ver_id_long.clear()
                    for version in versions:
                        if version["type"] not in ["snapshot", "old_alpha", "old_beta"]:
                            ver_id_main.append(version["id"])
                        else:
                            if version["type"] == "snapshot":
                                ver_id_short.append(version["id"])
                            elif version["type"] in ["old_alpha", "old_beta"]:
                                ver_id_long.append(version["id"])
                    minecraft_choose.clear()
                    if version_type == "百络谷支持版本":
                        minecraft_choose.addItems(ver_id_bloret)
                    elif version_type == "正式版本":
                        minecraft_choose.addItems(ver_id_main)
                    elif version_type == "快照版本":
                        minecraft_choose.addItems(ver_id_short)
                    elif version_type == "远古版本":
                        minecraft_choose.addItems(ver_id_long)
                    else:
                        self.log("未知的版本类型", logging.ERROR)
                    self.log(f"最新发布版本: {latest_release}")
                    self.log(f"最新快照版本: {latest_snapshot}")
                    self.log("Minecraft 版本列表已更新")
                else:
                    self.log("无法获取 Minecraft 版本列表", logging.ERROR)
            except requests.exceptions.RequestException as e:
                self.log(f"请求错误: {e}", logging.ERROR)
                TeachingTip.create(
                    target=minecraft_choose,
                    icon=InfoBarIcon.ERROR,
                    title='提示',
                    content="无法连接到服务器，请检查网络连接或稍后再试。",
                    isClosable=True,
                    tailPosition=TeachingTipTailPosition.BOTTOM,
                    duration=2000,
                    parent=self
                )
            except requests.exceptions.SSLError as e:
                self.log(f"SSL 错误: {e}", logging.ERROR)
                TeachingTip.create(
                    target=minecraft_choose,
                    icon=InfoBarIcon.ERROR,
                    title='提示',
                    content="无法连接到服务器，请检查网络连接或稍后再试。",
                    isClosable=True,
                    tailPosition=TeachingTipTailPosition.BOTTOM,
                    duration=2000,
                    parent=self
                )
            finally:
                for dialog in self.loading_dialogs:  # 关闭所有 loading_dialog
                    dialog.close()
                self.loading_dialogs.clear()  # 清空列表
    def start_download(self, widget):
        minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
        download_button = widget.findChild(QPushButton, "download")
        if minecraft_choose and download_button:
            # 覆盖 cmcl.json 文件
            cmcl_save_path = os.path.join(os.getcwd(), "cmcl_save.json")
            cmcl_path = os.path.join(os.getcwd(), "cmcl.json")
            if os.path.exists(cmcl_save_path):
                try:
                    shutil.copy(cmcl_save_path, cmcl_path)
                    self.log(f"成功覆盖 {cmcl_path} 文件")
                except Exception as e:
                    self.log(f"覆盖 {cmcl_path} 文件失败: {e}", logging.ERROR)
            choose_ver = minecraft_choose.currentText()
            teaching_tip = TeachingTip.create(
                target=widget,
                icon=InfoBarIcon.SUCCESS,
                title='正在下载',
                content="请稍等",
                isClosable=True,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                duration=0,  # 设置为0表示不自动关闭
                parent=self
            )
            teaching_tip.move(download_button.mapToGlobal(download_button.rect().topLeft()))
            cmcl_path = os.path.join(os.getcwd(), self.cmcl_command)
            self.download_thread = self.DownloadThread(cmcl_path, choose_ver, self.log)
            self.threads.append(self.download_thread)  # 将线程添加到列表中
            self.download_thread.output_received.connect(self.log_output)
            self.download_thread.output_received.connect(lambda text: download_button.setText(text[:70] + '...' if len(text) > 70 else text))  # 实时更新按钮文字
            self.download_thread.finished.connect(lambda: self.on_download_finished(teaching_tip, download_button))
            self.download_thread.error_occurred.connect(lambda error: self.on_download_error(error, teaching_tip, download_button))
            self.download_thread.start()
    def setup_loading_gif(self, label):
        movie = QMovie("ui/icon/loading2.gif")
        label.setMovie(movie)
        movie.start()
    class DownloadThread(QThread):
        finished = pyqtSignal()
        error_occurred = pyqtSignal(str)
        output_received = pyqtSignal(str)
        def __init__(self, cmcl_path, version, log_method):
            self.log = log_method
            super().__init__()
            self.cmcl_path = cmcl_path
            self.version = version
        def run(self):
            try:
                self.log(f"正在下载版本 {self.version}")
                self.log("执行命令: " + f"{self.cmcl_path} install {self.version}")
                process = subprocess.Popen(
                    [self.cmcl_path, "install", self.version],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding=None
                )
                for line in iter(process.stdout.readline, ''):
                    if "该名称已存在，请更换一个名称。" in line:
                        self.error_occurred.emit("该版本已下载过。")
                        process.terminate()
                        return
                    self.output_received.emit(line.strip())
                    self.log(line.strip())  # 将输出存入日志
                while process.poll() is None:
                    self.output_received.emit("正在下载并安装")
                    time.sleep(1)
                for line in iter(process.stdout.readline, ''):
                    self.output_received.emit(line.strip().encode('utf-8', errors='replace').decode('utf-8'))  # 修改这里
                    self.log(line.strip().encode('utf-8', errors='replace').decode('utf-8'))  # 将输出存入日志
                process.stdout.close()
                process.wait()
                if process.returncode == 0:
                    self.finished.emit()
                else:
                    self.error_occurred.emit(process.stderr.read().strip())
            except subprocess.CalledProcessError as e:
                self.error_occurred.emit(str(e.stderr))
    # def on_download_error(self, error_message, widget, teaching_tip):
    #     download_button = widget.findChild(QPushButton, "download")
    #     if download_button:
    #         teaching_tip.close()
    #         TeachingTip.create(
    #             target=download_button,
    #             icon=InfoBarIcon.ERROR,
    #             title='提示',
    #             content=f"下载失败，原因：{error_message}",
    #             isClosable=True,
    #             tailPosition=TeachingTipTailPosition.BOTTOM,
    #             duration=2000,
    #             parent=self
    #         )
    def on_download_finished(self, teaching_tip, download_button):
        if teaching_tip and not sip.isdeleted(teaching_tip):
            teaching_tip.close()
        if download_button:
            TeachingTip.create(
                target=download_button,
                icon=InfoBarIcon.SUCCESS,
                title='下载成功',
                content="版本已成功下载",
                isClosable=True,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                duration=2000,
                parent=self
            )
        self.run_cmcl_list()  # 完成下载任务后运行 cmcl -l 获取列表
        # 拷贝 servers.dat 文件到 .minecraft 文件夹
        src_file = os.path.join(os.getcwd(), "servers.dat")
        dest_dir = os.path.join(os.getcwd(), ".minecraft")
        if os.path.exists(src_file):
            try:
                shutil.copy(src_file, dest_dir)
                self.log(f"成功拷贝 {src_file} 到 {dest_dir}")
            except Exception as e:
                self.log(f"拷贝 {src_file} 到 {dest_dir} 失败: {e}", logging.ERROR)
        self.is_running = False  # 重置标志变量
        # 发送系统通知
        QTimer.singleShot(0, lambda: self.send_system_notification("下载完成", f"版本 {self.download_thread.version} 已成功下载"))
    def send_system_notification(self, title, message):
        try:
            if sys.platform == "win32":
                toaster = ToastNotifier()
                toaster.show_toast(title, message, duration=10)
            elif sys.platform == "darwin":
                subprocess.run(["osascript", "-e", f'display notification "{message}" with title "{title}"'])
            else:
                subprocess.run(["notify-send", title, message])
        except Exception as e:
            self.log(f"发送系统通知失败: {e}", logging.ERROR)
    def on_download_error(self, error_message, teaching_tip, download_button):
        if teaching_tip and not sip.isdeleted(teaching_tip):
            teaching_tip.close()
        TeachingTip.create(
            target=download_button,
            icon=InfoBarIcon.ERROR,
            title='提示',
            content=f"下载失败，原因：{error_message}",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=2000,
            parent=self
        )
        self.is_running = False  # 重置标志变量
    # def update_minecraft_versions(self, minecraft_choose, show_all):
    #     try:
    #         response = requests.get("https://bmclapi2.bangbang93.com/mc/game/version_manifest.json")
    #         response.raise_for_status()
    #         version_data = response.json()
    #         versions = version_data["versions"]
    #         ver_id.clear()
    #         ver_id_main.clear()
    #         ver_url.clear()
    #         for version in versions:
    #             ver_id.append(version["id"])
    #             ver_url[version["id"]] = version["url"]
    #             if version["type"] not in ["snapshot", "old_alpha", "old_beta"]:
    #                 ver_id_main.append(version["id"])
    #         minecraft_choose.clear()
    #         if show_all:
    #             minecraft_choose.addItems(ver_id)
    #         else:
    #             minecraft_choose.addItems(ver_id_main)
    #         logging.info("Minecraft 版本列表已更新")
    #     except requests.RequestException as e:
    #         logging.error(f"无法获取 Minecraft 版本列表: {e}")
    #         QMessageBox.critical(self, "错误", f"无法获取 Minecraft 版本列表: {e}")
    def handle_first_run(self):
        if self.config.getboolean('DEFAULT', 'first-run', fallback=True):
            parent_dir = os.path.dirname(os.getcwd())
            updating_folder = os.path.join(parent_dir, "updating")
            updata_ps1_file = os.path.join(parent_dir, "updata.ps1")
            if os.path.exists(updating_folder):
                subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-Command", f"Remove-Item -Path '{updating_folder}' -Recurse -Force"], check=True)
                self.log(f"删除文件夹: {updating_folder}")
            if os.path.exists(updata_ps1_file):
                os.remove(updata_ps1_file)
                self.log(f"删除文件: {updata_ps1_file}")
                def create_shortcut(self):
                    desktop = os.path.join(os.path.join(os.environ['USERPROFILE']), 'Desktop')
                    shortcut_path = os.path.join(desktop, 'Bloret Launcher.lnk')
                    target = os.path.join(os.getcwd(), 'Bloret-Launcher.exe')
                    icon = os.path.join(os.getcwd(), 'icons', 'bloret.ico')
                    shell = Dispatch('WScript.Shell')
                    shortcut = shell.CreateShortCut(shortcut_path)
                    shortcut.TargetPath = target
                    shortcut.WorkingDirectory = os.getcwd()
                    shortcut.IconLocation = icon
                    shortcut.save()
                self.create_shortcut()
            #首次启动向 http://pcfs.top:2/api/blnum 发送请求，服务器计数器+1
            #具体可见项目 https://github.com/BloretCrew/Bloret-Launcher-Server
            response = requests.get("http://pcfs.top:2/api/blnum")
            if response.status_code == 200:
                data = response.json()
                self.bl_users = data.get("user", "未知用户")
                self.log(f"获取到的用户数: {self.bl_users}")
            else:
                self.bl_users = "未知用户"
                self.log("无法获取用户数", logging.ERROR)

            #首次启动显示弹窗提醒
            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setWindowTitle('欢迎')
            msg_box.setText("欢迎使用百络谷启动器 (＾ｰ^)ノ\n您是百络谷启动器的第 %s 位用户" % self.bl_users)
            msg_box.setWindowIcon(QIcon("icons/bloret.png"))  # 设置弹窗图标
            msg_box.setStandardButtons(QMessageBox.Ok)
            msg_box.exec()
            # QMessageBox.information(self, "欢迎", "欢迎使用百络谷启动器 (＾ｰ^)ノ\n您是百络谷启动器的第 %s 位用户" % self.bl_users)
            # 更新配置文件中的 first-run 值
            self.config.set('DEFAULT', 'first-run', 'false')
            with open('config.ini', 'w', encoding='utf-8') as configfile:
                self.config.write(configfile)
    def check_for_updates(self):
        self.BL_latest_ver = self.get_latest_version()
        self.log(f"最新正式版: {self.BL_latest_ver}")
        BL_ver = float(self.config.get('DEFAULT', 'ver', fallback='0.0'))  # 从config.ini读取当前版本
        if BL_ver < float(self.BL_latest_ver):
            self.log(f"当前版本不是最新版，请更新到 {self.BL_latest_ver} 版本", logging.WARNING)

            msg_box = QMessageBox(self)
            msg_box.setIcon(QMessageBox.Warning)
            msg_box.setWindowTitle('版本更新提示')
            msg_box.setText(f'当前版本不是最新版，请更新到 {self.BL_latest_ver} 版本')
            msg_box.setWindowIcon(QIcon("icons/bloret.png"))  # 设置弹窗图标
            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg_box.button(QMessageBox.Ok).setText('立即更新')
            msg_box.button(QMessageBox.Cancel).setText('暂时不了')
            if msg_box.exec() == QMessageBox.Ok:
                self.update_to_latest_version()
    def update_to_latest_version(self):
        #url = f"http://localhost:100/zipdownload/{self.BL_latest_ver}.zip"
        url = f"http://123.129.241.101:30399/zipdownload/{self.BL_latest_ver}.zip"
        save_path = os.path.join(os.getcwd(), f"{self.BL_latest_ver}.zip")
        updating_folder = os.path.join(os.path.dirname(os.getcwd()), "updating")
        if not os.path.exists(updating_folder):
            os.makedirs(updating_folder)
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(save_path, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            self.log(f"版本 {self.BL_latest_ver} 下载成功，保存路径: {save_path}")
            # 将下载的文件移动到 updating 文件夹
            new_save_path = os.path.join(updating_folder, f"{self.BL_latest_ver}.zip")
            os.rename(save_path, new_save_path)
            # 解压缩文件到 updating 文件夹
            with zipfile.ZipFile(new_save_path, 'r') as zip_ref:
                zip_ref.extractall(updating_folder)
            self.log(f"版本 {self.BL_latest_ver} 解压缩成功，路径: {updating_folder}")
            # 删除压缩包
            os.remove(new_save_path)
            self.log(f"删除压缩包: {new_save_path}")
            # 移动 .minecraft 文件夹到 updating 文件夹
            minecraft_folder = os.path.join(os.getcwd(), ".minecraft")
            if os.path.exists(minecraft_folder):
                new_minecraft_folder = os.path.join(updating_folder, ".minecraft")
                os.rename(minecraft_folder, new_minecraft_folder)
                self.log(f"移动 .minecraft 文件夹到: {new_minecraft_folder}")
            # 创建 updata.ps1 文件
            current_folder_name = os.path.basename(os.getcwd())
            bat_file_path = os.path.join(os.path.dirname(os.getcwd()), "updata.ps1")
            with open(bat_file_path, 'w', encoding='utf-8') as bat_file:
                bat_file.write(f'cd "{os.path.dirname(os.getcwd())}"\n')
                bat_file.write(f'taskkill /im Bloret-Launcher.exe /f\n')
                bat_file.write(f'Start-Sleep -Seconds 2\n')
                bat_file.write(f'Remove-Item -Path ".\\{current_folder_name}" -Recurse -Force\n')
                bat_file.write(f'Move-Item -Path ".\\updating\\*" -Destination ".\\{current_folder_name}"\n')
                bat_file.write(f'cd "{os.path.join(os.path.dirname(os.getcwd()), "Bloret-Launcher")}"\n')
                bat_file.write(f'Start-Process -FilePath "Bloret-Launcher.exe"\n')
            self.log(f"创建 updata.ps1 文件: {bat_file_path}")
            QMessageBox.information(self, "即将安装", f"版本 {self.BL_latest_ver} 即将开始安装")

            # 运行 updata.ps1 文件
            subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", bat_file_path], check=True)
            self.log(f"运行 updata.ps1 文件: {bat_file_path}")
        except requests.RequestException as e:
            self.log(f"下载版本 {self.BL_latest_ver} 失败: {e}", logging.ERROR)
            QMessageBox.critical(self, "下载失败", f"下载版本 {self.BL_latest_ver} 失败: {e}")
        except zipfile.BadZipFile as e:
            self.log(f"解压缩版本 {self.BL_latest_ver} 失败: {e}", logging.ERROR)
            QMessageBox.critical(self, "解压缩失败", f"解压缩版本 {self.BL_latest_ver} 失败: {e}")
        except OSError as e:
            self.log(f"文件操作失败: {e}", logging.ERROR)
            QMessageBox.critical(self, "文件操作失败", f"文件操作失败: {e}")
        except subprocess.CalledProcessError as e:
            self.log(f"运行 updata.ps1 文件失败: {e}", logging.ERROR)
            QMessageBox.critical(self, "更新失败", f"运行 updata.ps1 文件失败: {e}")
    def toggle_show_all_versions(self, state):
        widget = self.findChild(QWidget, "downloadWidget")  # 假设你的下载界面的QWidget对象名称为downloadWidget
        if widget:
            minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
            show_all_versions = widget.findChild(QCheckBox, "show_all_versions")
            if minecraft_choose and show_all_versions:
                self.update_minecraft_versions(widget, show_all=state)
    
    def open_bloret_web(self):
        QDesktopServices.openUrl(QUrl("http://pcfs.top:2"))
        self.log("打开 Bloret Launcher 网页")
    def open_github_bloret(self):
        QDesktopServices.openUrl(QUrl("https://github.com/BloretCrew"))
        self.log("打开Bloret Github 组织页面")
    def copy_skin_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_skin)
        self.log(f"皮肤URL {self.player_skin} 已复制到剪贴板")
    def copy_cape_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_cape)
        self.log(f"披风URL {self.player_cape} 已复制到剪贴板")
    def open_skin_url(self, widget):
        QDesktopServices.openUrl(QUrl(self.player_skin))
        self.log(f"打开皮肤URL: {self.player_skin}")
    def open_cape_url(self, widget):
        QDesktopServices.openUrl(QUrl(self.player_cape))
        self.log(f"打开披风URL: {self.player_cape}")
    def query_player_name(self, widget):
        player_uuid_edit = widget.findChild(QLineEdit, "search_name_type")
        name_result_label = widget.findChild(QLabel, "search_name")
        if player_uuid_edit and name_result_label:
            name_result_label.setText("查询中，请稍等...")
            player_uuid = player_uuid_edit.text()
            response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{player_uuid}")
            if response.status_code == 200:
                player_data = response.json()
                self.player_name = player_data.get("name", "未找到名称")
                name_result_label.setText(self.player_name)
                self.log(f"查询UUID {player_uuid} 的名称: {self.player_name}")
            else:
                name_result_label.setText("查询失败")
                self.log(f"查询UUID {player_uuid} 的名称失败", logging.ERROR)
    def copy_name_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_name)
        self.log(f"名称 {self.player_name} 已复制到剪贴板")
    def open_github_bloret_Launcher(self):
        QDesktopServices.openUrl(QUrl("https://github.com/BloretCrew/Bloret-Launcher"))
        self.log("打开该项目的Github页面")
    def open_qq_link(self):
        QDesktopServices.openUrl(QUrl("https://qm.qq.com/q/iGw0GwUCiI"))
        self.log("打开Bloret QQ 群页面")
    def animate_sidebar(self):
        start_geometry = self.navigationInterface.geometry()  # 修正拼写错误
        end_geometry = QRect(start_geometry.x(), start_geometry.y(), start_geometry.width(), start_geometry.height())
        self.sidebar_animation.setStartValue(start_geometry)
        self.sidebar_animation.setEndValue(end_geometry)
        self.sidebar_animation.start()
    def animate_fade_in(self):
        self.fade_in_animation.start()
    def apply_theme(self):
        theme = self.settings.value("theme", "light")
        if theme == "dark":
            self.setStyleSheet("QWidget { background-color: #2e2e2e; color: #ffffff; }")
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor("#2e2e2e"))
            palette.setColor(QPalette.WindowText, QColor("#ffffff"))
            palette.setColor(QPalette.Base, QColor("#1e1e1e"))
            palette.setColor(QPalette.AlternateBase, QColor("#2e2e2e"))
            palette.setColor(QPalette.ToolTipBase, QColor("#ffffff"))
            palette.setColor(QPalette.ToolTipText, QColor("#ffffff"))
            palette.setColor(QPalette.Text, QColor("#ffffff"))
            palette.setColor(QPalette.Button, QColor("#2e2e2e"))
            palette.setColor(QPalette.ButtonText, QColor("#ffffff"))
            palette.setColor(QPalette.BrightText, QColor("#ff0000"))
            palette.setColor(QPalette.Link, QColor("#2a82da"))
            palette.setColor(QPalette.Highlight, QColor("#2a82da"))
            palette.setColor(QPalette.HighlightedText, QColor("#000000"))
            self.setPalette(palette)
        else:
            self.setStyleSheet("")
            self.setPalette(self.style().standardPalette())
    def setup_passport_ui(self, widget):
        player_name_edit = widget.findChild(QLineEdit, "player_name")
        player_name_set_button = widget.findChild(QPushButton, "player_name_set")
        if player_name_edit and player_name_set_button:
            player_name_set_button.clicked.connect(lambda: self.on_player_name_set_clicked(widget))
            # 读取 cmcl.json 中的 playerName 并设置到输入框中
            try:
                with open('cmcl.json', 'r', encoding='utf-8') as file:
                    data = json.load(file)
                player_name = data['accounts'][0].get('playerName', '')
                player_name_edit.setText(player_name)
                self.log(f"读取到的 playerName: {player_name}")
            except (FileNotFoundError, json.JSONDecodeError, KeyError) as e:
                self.log(f"读取 cmcl.json 失败: {e}", logging.ERROR)
                player_name_edit.setText('')  # 如果读取失败，清空输入框

    # -----------------------------------------------------------
    # 以下内容是对于UI文件中各个元素的设定
    # -----------------------------------------------------------
    
    def on_home_clicked(self):
        self.log("主页 被点击")
        self.load_ui("ui/home.ui")
    def on_passport_clicked(self):
        self.log("通行证 被点击")
        self.load_ui("ui/passport.ui")
    def on_settings_clicked(self):
        self.log("设置 被点击")
        self.load_ui("ui/settings.ui")
    def on_info_clicked(self):
        self.log("关于 被点击")
        self.load_ui("ui/info.ui")
    def on_tools_clicked(self):
        self.log("工具 被点击")
        self.load_ui("ui/tools.ui")
    def on_button_clicked(self):
        self.log("按钮 被点击")
    def on_player_name_set_clicked(self, widget):
        player_name_edit = widget.findChild(QLineEdit, "player_name")
        player_name = player_name_edit.text()

        if not player_name:
            TeachingTip.create(
                target=self.sender(),
                icon=InfoBarIcon.ERROR,
                title='提示',
                content="请填写值后设定",
                isClosable=True,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                duration=2000,
                parent=self
            )
        elif any('\u4e00' <= char <= '\u9fff' for char in player_name):
            TeachingTip.create(
                target=self.sender(),
                icon=InfoBarIcon.ERROR,
                title='提示',
                content="名称不能包含中文",
                isClosable=True,
                tailPosition=TeachingTipTailPosition.BOTTOM,
                duration=2000,
                parent=self
            )
        else:
            with open('cmcl.json', 'r', encoding='utf-8') as file:
                data = json.load(file)
            data['accounts'][0]['playerName'] = player_name
            with open('cmcl.json', 'w', encoding='utf-8') as file:
                json.dump(data, file, ensure_ascii=False, indent=4)

    def setup_home_ui(self, widget):
        github_org_button = widget.findChild(QPushButton, "pushButton_2")
        if github_org_button:
            github_org_button.clicked.connect(self.open_github_bloret)
        github_project_button = widget.findChild(QPushButton, "pushButton")
        if github_project_button:
            github_project_button.clicked.connect(self.open_github_bloret_Launcher)
        
        # 插入以下代码
        openblweb_button = widget.findChild(QPushButton, "openblweb")
        if openblweb_button:
            openblweb_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("http://pcfs.top:2")))
        
        self.run_cmcl_list()
        run_choose = widget.findChild(ComboBox, "run_choose")
        if run_choose:
            run_choose.addItems(set_list)
        run_button = widget.findChild(QPushButton, "run")
        if run_button:
            run_button.clicked.connect(lambda: self.run_cmcl(run_choose.currentText()))
        self.show_text = widget.findChild(QLabel, "show")
    def run_cmcl(self, version):
        if self.is_running:
            self.log("run.ps1 正在运行中，不启动新的实例")
            return
        self.is_running = True  # 设置标志变量为True
        self.log(f"正在启动 {version}")
        run_button = self.sender()  # 获取按钮对象
        teaching_tip = TeachingTip.create(
            target=run_button,  # 修改为按钮对象
            icon=InfoBarIcon.SUCCESS,
            title=f'正在启动 {version}',
            content="请稍等",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=0,  # 设置为0表示不自动关闭
            parent=self
        )
        if teaching_tip:
            teaching_tip.move(run_button.mapToGlobal(run_button.rect().topLeft()))
    def log_output(self, output):
        self.log(output)
    def on_run_script_finished(self, teaching_tip, run_button):
        # ...existing code...
        if self.update_show_text_thread:
            self.update_show_text_thread.terminate()  # 停止更新线程
        # ...existing code...
        if teaching_tip and not sip.isdeleted(teaching_tip):
            teaching_tip.close()  # 关闭气泡消息
        TeachingTip.create(
            target=run_button,
            icon=InfoBarIcon.SUCCESS,
            title='游戏结束',
            content="Minecraft 已结束\n如果您认为是异常退出，请查看 log 文件夹中的最后一份日志文件\n并前往本项目的 Github 或 百络谷QQ群 询问",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=5000,
            parent=self
        )
        # 移除以下代码，避免重复启动线程
        # self.run_script_thread = RunScriptThread()
        # self.run_script_thread.output_received.connect(self.log_output)
        # self.run_script_thread.finished.connect(lambda: self.on_run_script_finished(teaching_tip, run_button))
        # self.run_script_thread.error_occurred.connect(lambda error: self.on_run_script_error(error, teaching_tip, run_button))
        # self.run_script_thread.start()

        self.is_running = False  # 重置标志变量

    def on_run_script_error(self, error, teaching_tip, run_button):
        # ...existing code...
        if self.update_show_text_thread:
            self.update_show_text_thread.terminate()  # 停止更新线程
        # ...existing code...
        if teaching_tip and not sip.isdeleted(teaching_tip):
            teaching_tip.close()
        TeachingTip.create(
            target=run_button,
            icon=InfoBarIcon.ERROR,
            title='提示',
            content=f"run.ps1 运行失败: {error}",
            isClosable=True,
            tailPosition=TeachingTipTailPosition.BOTTOM,
            duration=2000,
            parent=self
        )
        self.log(f"run.ps1 运行失败: {error}", logging.ERROR)
        self.is_running = False  # 重置标志变量
    def update_show_text(self, text):
        self.show_text.setText(text)  # 更新show文字框的内容
    def setup_download_load_ui(self, widget):
        loading_label = widget.findChild(QLabel, "loading_label")
        if loading_label:
            self.setup_loading_gif(loading_label)
    # def se tup_download_ui(self, widget):
    #     # 设置下载界面的UI元素
    #     minecraft_choose = widget.findChild(ComboBox, "minecraft_choose")
    #     show_all_versions = widget.findChild(QCheckBox, "show_all_versions")
    #     if minecraft_choose and show_all_versions:
    #         show_all_versions.stateChanged.connect(lambda state: self.update_minecraft_versions(minecraft_choose, state == Qt.Checked))
    #         self.update_minecraft_versions(minecraft_choose, show_all_versions.isChecked())
    def get_minecraft_versions(self, show_all):
        # 模拟获取 Minecraft 版本列表
        if show_all:
            return ["1.18.1", "1.18", "1.17.1", "1.17", "1.16.5", "1.16.4", "1.16.3", "1.16.2", "1.16.1", "1.16"]
        else:
            return ["1.18.1", "1.17.1", "1.16.5"]
    def setup_tools_ui(self, widget):
        name2uuid_button = widget.findChild(QPushButton, "name2uuid_player_Button")
        if name2uuid_button:
            name2uuid_button.clicked.connect(lambda: self.query_player_uuid(widget))
        search_name_button = widget.findChild(QPushButton, "search_name_button")
        if search_name_button:
            search_name_button.clicked.connect(lambda: self.query_player_name(widget))
        skin_search_button = widget.findChild(QPushButton, "skin_search_button")
        if skin_search_button:
            skin_search_button.clicked.connect(lambda: self.query_player_skin(widget))
        name_copy_button = widget.findChild(QPushButton, "search_name_copy")
        if name_copy_button:
            name_copy_button.clicked.connect(lambda: self.copy_name_to_clipboard(widget))
        uuid_copy_button = widget.findChild(QPushButton, "pushButton_5")
        if uuid_copy_button:
            uuid_copy_button.clicked.connect(lambda: self.copy_uuid_to_clipboard(widget))
        skin_copy_button = widget.findChild(QPushButton, "search_skin_copy")
        if skin_copy_button:
            skin_copy_button.clicked.connect(lambda: self.copy_skin_to_clipboard(widget))
        cape_copy_button = widget.findChild(QPushButton, "search_cape_copy")
        if cape_copy_button:
            cape_copy_button.clicked.connect(lambda: self.copy_cape_to_clipboard(widget))
    def copy_uuid_to_clipboard(self, widget):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.player_uuid)
        self.log(f"UUID {self.player_uuid} 已复制到剪贴板")
    def download_skin(self, widget):
        if self.player_skin:
            skin_url = self.player_skin
            skin_data = requests.get(skin_url).content
            with open("player_skin.png", "wb") as file:
                file.write(skin_data)
            self.log(f"皮肤已下载到 player_skin.png")
    def download_cape(self, widget):
        if self.player_cape:
            cape_url = self.player_cape
            cape_data = requests.get(cape_url).content
            with open("player_cape.png", "wb") as file:
                file.write(cape_data)
            self.log(f"披风已下载到 player_cape.png")
    def query_player_uuid(self, widget):
        player_name_edit = widget.findChild(QLineEdit, "name2uuid_player_uuid")
        uuid_result_label = widget.findChild(QLabel, "label_2")
        if player_name_edit and uuid_result_label:
            uuid_result_label.setText("查询中，请稍等...")
            player_name = player_name_edit.text()
            response = requests.get(f"https://api.mojang.com/users/profiles/minecraft/{player_name}")
            if response.status_code == 200:
                player_data = response.json()
                self.player_uuid = player_data.get("id", "未找到UUID")
                uuid_result_label.setText(self.player_uuid)
                self.log(f"查询玩家名称 {player_name} 的UUID: {self.player_uuid}")
            else:
                uuid_result_label.setText("查询失败")
                self.log(f"查询玩家名称 {player_name} 的UUID失败", logging.ERROR)
    def query_player_skin(self, widget):
        skin_uuid_edit = widget.findChild(QLineEdit, "skin_uuid")
        skin_result_label = widget.findChild(QLabel, "search_skin")
        cape_result_label = widget.findChild(QLabel, "search_cape")
        if skin_uuid_edit and skin_result_label and cape_result_label:
            skin_result_label.setText("查询中，请稍等...")
            cape_result_label.setText("查询中，请稍等...")
            player_uuid = skin_uuid_edit.text()
            response = requests.get(f"https://sessionserver.mojang.com/session/minecraft/profile/{player_uuid}")
            if response.status_code == 200:
                player_data = response.json()
                properties = player_data.get("properties", [])
                for prop in properties:
                    if prop["name"] == "textures":
                        textures = json.loads(base64.b64decode(prop["value"]).decode("utf-8"))
                        self.player_skin = textures["textures"].get("SKIN", {}).get("url", "未找到皮肤")
                        self.player_cape = textures["textures"].get("CAPE", {}).get("url", "未找到披风")
                        skin_result_label.setText(self.player_skin[:12] + "..." if len(self.player_skin) > 12 else self.player_skin)
                        cape_result_label.setText(self.player_cape[:12] + "..." if len(self.player_cape) > 12 else self.player_cape)
                        self.log(f"查询玩家UUID {player_uuid} 的皮肤: {self.player_skin}")
                        self.log(f"查询玩家UUID {player_uuid} 的披风: {self.player_cape}")
                        break
            else:
                skin_result_label.setText("查询失败")
                cape_result_label.setText("查询失败")
                self.log(f"查询玩家UUID {player_uuid} 的皮肤和披风失败", logging.ERROR)
    def setup_settings_ui(self, widget):
        # 设置设置界面的UI元素
        pass
    def get_latest_version(self):
        try:
            response = requests.get("https://api.github.com/repos/BloretCrew/Bloret-Launcher/releases/latest")
            if response.status_code == 200:
                latest_release = response.json()
                return latest_release.get("tag_name", "未知版本")
            else:
                self.log("查询最新版本失败", logging.ERROR)
                return "未知版本"
        except requests.RequestException as e:
            self.log(f"查询最新版本时发生错误: {e}", logging.ERROR)
            return "未知版本"
    def setup_info_ui(self, widget):
        github_org_button = widget.findChild(QPushButton, "pushButton_2")
        if github_org_button:
            github_org_button.clicked.connect(self.open_github_bloret)
        github_project_button = widget.findChild(QPushButton, "button_github")
        if github_project_button:
            github_project_button.clicked.connect(self.open_github_bloret_Launcher)
        qq_group_button = widget.findChild(QPushButton, "pushButton")
        if qq_group_button:
            qq_group_button.clicked.connect(self.open_qq_link)
        qq_icon = widget.findChild(QLabel, "QQ_icon")
        if qq_icon:
            qq_icon.setPixmap(QPixmap("ui/icon/qq.png"))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
