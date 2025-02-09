import datetime


def get_now_date():
    now = datetime.datetime.now()
    formatted = now.strftime("%Y-%m-%d-%H-%M-%S")
    return formatted
