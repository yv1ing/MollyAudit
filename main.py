import json
import os
import warnings
from audit import Audit


warnings.simplefilter('ignore', FutureWarning)

os.environ['OPENAI_API_BASE'] = 'https://yunwu.ai/v1'
os.environ['OPENAI_API_KEY'] = 'sk-FdKVL1IiRCMhTVScD4iIEfE2U7978rKuAQhPl0Gbr55l6fDD'

fortify_rules = json.load(open('fortify_rules.json', 'r', encoding='utf-8'))


def result_callback(result):
    pass


if __name__ == '__main__':
    src_root = r'C:\Users\yvling\Desktop\PHP-Vuln'
    language = 'php'

    audit = Audit(fortify_rules)
    audit.load_source_files(src_root, language)
    audit.audit(result_callback)

