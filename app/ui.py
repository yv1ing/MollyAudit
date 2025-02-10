import os
import re
import datetime
import threading
from threading import Event
from app import audit_code, real_update_config, GLOBAL_CONFIG
from logger import Logger
from PyQt6.QtGui import QColor, QGuiApplication, QTextCursor
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QTextEdit,
    QComboBox
)

BACKGROUND_COLOR = '#dcdcdc'
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
ANSI_COLOR_REGEX = re.compile(r'\x1B\[(?:([0-9]+);)?([0-9]+)m')
ANSI_COLOR_MAP = {
    '94': QColor(0, 0, 200),
    '92': QColor(0, 128, 0),
    '93': QColor(255, 127, 0),
    '91': QColor(220, 0, 0),
    '95': QColor(180, 0, 180)
}


def get_now_date():
    now = datetime.datetime.now()
    formatted = now.strftime("%Y-%m-%d-%H-%M-%S")
    return formatted


def convert_ansi_to_rich_text(text):
    segments = []
    pos = 0
    for match in ANSI_COLOR_REGEX.finditer(text):
        start, end = match.span()
        if start > pos:
            segments.append(text[pos:start])
        color_code = match.group(2)
        if color_code in ANSI_COLOR_MAP:
            color = ANSI_COLOR_MAP[color_code]
            html_color = color.name()
            segments.append(f'<span style="color:{html_color}">')
        else:
            segments.append('<span>')
        pos = end
    segments.append(text[pos:])
    segments.append('</span>')
    rich_text = ''.join(segments)
    rich_text = ANSI_ESCAPE.sub('', rich_text)

    return rich_text


class MainWindow(QWidget):
    def __init__(self):
        self.event = Event()
        self.log = Logger('app', callback=self.process_output_callback)

        super().__init__()
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        dir_lang_layout = QHBoxLayout()

        # 目录选择
        dir_layout = QHBoxLayout()
        self.dir_label = QLabel('项目目录:')
        self.dir_input = QLineEdit()
        self.dir_button = QPushButton('选择')
        self.dir_button.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_label)
        dir_layout.addWidget(self.dir_input)
        dir_layout.addWidget(self.dir_button)
        dir_lang_layout.addLayout(dir_layout)

        # 语言选择
        languages = ['c', 'cpp', 'go', 'php', 'jsp', 'java', 'python', 'javascript']
        self.lang_label = QLabel('项目语言:')
        self.lang_combobox = QComboBox()
        self.lang_combobox.addItems(languages)
        dir_lang_layout.addWidget(self.lang_label)
        dir_lang_layout.addWidget(self.lang_combobox)

        main_layout.addLayout(dir_lang_layout)

        # 配置信息
        config_layout = QHBoxLayout()
        self.base_url_label = QLabel('接口地址:')
        self.base_url_input = QLineEdit()
        self.api_key_label = QLabel('模型密钥:')
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        config_layout.addWidget(self.base_url_label)
        config_layout.addWidget(self.base_url_input)
        config_layout.addWidget(self.api_key_label)
        config_layout.addWidget(self.api_key_input)
        main_layout.addLayout(config_layout)

        model_layout = QHBoxLayout()
        self.cae_model_label = QLabel('模块分析模型:')
        self.cae_model_input = QLineEdit()
        self.csa_model_label = QLabel('代码审计模型:')
        self.csa_model_input = QLineEdit()
        model_layout.addWidget(self.cae_model_label)
        model_layout.addWidget(self.cae_model_input)
        model_layout.addWidget(self.csa_model_label)
        model_layout.addWidget(self.csa_model_input)
        main_layout.addLayout(model_layout)

        # 按钮部分
        button_layout = QHBoxLayout()
        self.start_button = QPushButton('开始审计')
        self.start_button.clicked.connect(self.start_process)
        self.stop_button = QPushButton('终止审计')
        self.stop_button.clicked.connect(self.stop_process)
        self.update_button = QPushButton('更新配置')
        self.update_button.clicked.connect(self.update_config)
        self.clear_button = QPushButton('清空输出')
        self.clear_button.clicked.connect(self.clear_panel)
        button_layout.addWidget(self.start_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.update_button)
        button_layout.addWidget(self.clear_button)
        main_layout.addLayout(button_layout)

        # 实时输出
        output_layout = QVBoxLayout()

        # 过程输出
        self.process_output_text = QTextEdit()
        self.process_output_text.setReadOnly(True)
        self.process_output_text.setStyleSheet(f'background-color: {BACKGROUND_COLOR};')
        output_layout.addWidget(self.process_output_text)

        # 结果输出
        self.result_output_text = QTextEdit()
        self.result_output_text.setReadOnly(True)
        self.result_output_text.setStyleSheet(f'background-color: {BACKGROUND_COLOR};')
        output_layout.addWidget(self.result_output_text)

        output_layout.setStretch(0, 1)
        output_layout.setStretch(1, 2)
        main_layout.addLayout(output_layout)

        self.setLayout(main_layout)
        self.setWindowTitle('茉莉审计 - by yvling')
        screen = QGuiApplication.primaryScreen().geometry()
        window_width = 1000
        window_height = 600
        x = (screen.width() - window_width) // 2
        y = (screen.height() - window_height) // 2
        self.setGeometry(x, y, window_width, window_height)

        # 导出结果
        export_button_layout = QHBoxLayout()
        link_label = QLabel(
            '联系作者：<a href="https://github.com/yv1ing">Github</a> <a href=mailto:me@yvling.cn>Email</a>'
        )
        link_label.setOpenExternalLinks(True)
        export_button_layout.addWidget(link_label)
        export_button_layout.addStretch(1)

        self.export_button = QPushButton('导出结果')
        self.export_button.clicked.connect(self.export_result)
        export_button_layout.addWidget(self.export_button)
        main_layout.addLayout(export_button_layout)

        # 加载配置
        self.base_url_input.setText(GLOBAL_CONFIG['base_url'])
        self.api_key_input.setText(GLOBAL_CONFIG['api_key'])
        self.cae_model_input.setText(GLOBAL_CONFIG['cae_model'])
        self.csa_model_input.setText(GLOBAL_CONFIG['csa_model'])

    def closeEvent(self, event):
        self.event.set()

    def clear_panel(self):
        self.process_output_text.clear()
        self.result_output_text.clear()

    def update_config(self):
        base_url = self.base_url_input.text()
        api_key = self.api_key_input.text()
        cae_model = self.cae_model_input.text()
        csa_model = self.csa_model_input.text()

        real_update_config('base_url', base_url)
        real_update_config('api_key', api_key)
        real_update_config('cae_model', cae_model)
        real_update_config('csa_model', csa_model)
        self.log.info('更新配置成功')

    def select_directory(self):
        directory = QFileDialog.getExistingDirectory(self, '选择项目目录')
        if directory:
            self.dir_input.setText(directory)

    def export_result(self):
        result_text = self.result_output_text.toPlainText()
        if result_text == '':
            self.log.warning('当前结果为空')
            return

        directory = QFileDialog.getExistingDirectory(self, '选择导出目录')
        if directory:
            file_name = f'molly-audit-{get_now_date()}.txt'
            file_path = os.path.join(directory, file_name).replace('\\', '/')
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(result_text)
                self.log.info(f'导出结果成功： {file_path}')
            except Exception as e:
                self.log.error(f'导出结果错误：{str(e)}')

    def process_output_callback(self, content):
        rich_text = convert_ansi_to_rich_text(content)
        self.process_output_text.append(rich_text)
        cursor = self.process_output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.process_output_text.setTextCursor(cursor)
        self.process_output_text.ensureCursorVisible()

    def result_output_callback(self, content):
        self.result_output_text.append(f'{content}\n')
        cursor = self.result_output_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.result_output_text.setTextCursor(cursor)
        self.result_output_text.ensureCursorVisible()

    def start_process(self):
        selected_dir = self.dir_input.text()
        selected_lang = self.lang_combobox.currentText()
        base_url = self.base_url_input.text()
        api_key = self.api_key_input.text()
        cae_model = self.cae_model_input.text()
        csa_model = self.csa_model_input.text()

        if not selected_dir or not base_url or not api_key:
            self.log.error('请确保项目目录、接口地址和模型密钥等都已填写')
            return

        self.log.info('正在加载所需资源')
        try:
            threading.Thread(
                target=audit_code,
                args=(
                    base_url,
                    api_key,
                    selected_dir,
                    selected_lang,
                    cae_model,
                    csa_model,
                    self.process_output_callback,
                    self.result_output_callback,
                    self.event
                )
            ).start()
        except Exception as e:
            self.log.error(f'发生异常：{str(e)}')
        finally:
            if 'OPENAI_API_BASE' in os.environ:
                del os.environ['OPENAI_API_BASE']
            if 'OPENAI_API_KEY' in os.environ:
                del os.environ['OPENAI_API_KEY']

    def stop_process(self):
        self.event.set()

        if 'OPENAI_API_BASE' in os.environ:
            del os.environ['OPENAI_API_BASE']
        if 'OPENAI_API_KEY' in os.environ:
            del os.environ['OPENAI_API_KEY']
        self.log.critical('已终止代码审计流程')
