import os
import warnings
from audit import Audit


warnings.simplefilter('ignore', FutureWarning)

os.environ['OPENAI_API_BASE'] = 'https://yunwu.ai/v1'
os.environ['OPENAI_API_KEY'] = 'sk-zpkHfWT0Zhvzc79lX11WS4dEyg5CkQ3RdZOSNDoLADaitfVM'


def result_callback(result):
    pass


if __name__ == '__main__':
    src_root = r'C:\Users\yvling\Desktop\JavaSecLab'
    language = 'java'

    audit = Audit()
    audit.load_source_files(src_root, language)
    audit.audit(result_callback)

