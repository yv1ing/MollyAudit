from datetime import datetime


LOG_COLORS = {
    'DEBUG': '\033[94m',    # 蓝色
    'INFO': '\033[92m',     # 绿色
    'WARNING': '\033[93m',  # 黄色
    'ERROR': '\033[91m',    # 红色
    'CRITICAL': '\033[95m'  # 紫色
}
RESET_COLOR = '\033[0m'


def log_with_color(level, message):
    color = LOG_COLORS.get(level, RESET_COLOR)
    prefix = f"[{level}]"
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    formatted_message = f"{color}{date} {prefix} {message}{RESET_COLOR}"

    print(formatted_message)


class Logger:
    def __init__(self, name):
        pass

    def debug(self, message):
        log_with_color("DEBUG", message)

    def info(self, message):
        log_with_color("INFO", message)

    def warning(self, message):
        log_with_color("WARNING", message)

    def error(self, message):
        log_with_color("ERROR", message)

    def critical(self, message):
        log_with_color("CRITICAL", message)
