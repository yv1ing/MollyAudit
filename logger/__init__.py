import time
from datetime import datetime

LOG_COLORS = {
    'DEBUG': '\033[94m',  # 蓝色
    'INFO': '\033[92m',  # 绿色
    'WARNING': '\033[93m',  # 黄色
    'ERROR': '\033[91m',  # 红色
    'CRITICAL': '\033[95m'  # 紫色
}
RESET_COLOR = '\033[0m'


class Logger:
    def __init__(self, name, callback):
        self.name = name
        self.callback = callback
        pass

    def debug(self, message):
        self.log_with_color("DEBUG", message)

    def info(self, message):
        self.log_with_color("INFO", message)

    def warning(self, message):
        self.log_with_color("WARNING", message)

    def error(self, message):
        self.log_with_color("ERROR", message)

    def critical(self, message):
        self.log_with_color("CRITICAL", message)

    def log_with_color(self, level, message):
        color = LOG_COLORS.get(level, RESET_COLOR)
        date = datetime.now().strftime('%H:%M:%S')

        prefix = f"[{date}]"
        formatted_message = f"{color}{prefix} {message}{RESET_COLOR}"

        print(formatted_message)
        if self.callback:
            self.callback(formatted_message)

        time.sleep(0.1)
