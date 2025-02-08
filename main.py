import os
import warnings
from audit import Audit


warnings.simplefilter('ignore', FutureWarning)

os.environ['OPENAI_API_BASE'] = 'https://yunwu.ai/v1'
os.environ['OPENAI_API_KEY'] = 'sk-SQhmr2wNQa2BpohUrxgJOFIDY9ODSxUkLQLWWlPD9qDNVsN1'


def result_callback(result):
    pass


if __name__ == '__main__':
    src_root = r'C:\Users\yvling\Desktop\PHP-Vuln'
    language = 'php'

    audit = Audit()
    audit.load_source_files(src_root, language)
    audit.audit(result_callback)

