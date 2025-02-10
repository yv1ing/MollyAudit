import os
import warnings
from audit import Audit

warnings.simplefilter('ignore', FutureWarning)

home_dir = os.path.expanduser("~")
config_file_name = ".mollyaudit"
config_file_path = os.path.join(home_dir, config_file_name)

GLOBAL_CONFIG = {
    "base_url": "https://openai.com/v1",
    "api_key": "",
    "reasoning_model": "o3-mini-all",
    "embedding_model": "text-embedding-3-small"
}


def load_config():
    global GLOBAL_CONFIG

    if os.path.exists(config_file_path):
        with open(config_file_path, 'r') as file:
            for line in file:
                line = line.strip()
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    GLOBAL_CONFIG[key] = value
    else:
        with open(config_file_path, 'w') as file:
            for key, value in GLOBAL_CONFIG.items():
                file.write(f"{key}={value}\n")


def update_config(key, value):
    global GLOBAL_CONFIG

    GLOBAL_CONFIG[key] = value
    with open(config_file_path, 'w') as file:
        for k, v in GLOBAL_CONFIG.items():
            file.write(f"{k}={v}\n")


def audit_code(base_url, api_key, src_root, language, reasoning_model, embedding_model, process_output_callback,
               result_output_callback, event):
    audit = Audit(base_url, api_key, reasoning_model, embedding_model, process_output_callback, result_output_callback)
    audit.build_directory_tree(src_root, language)
    audit.audit(event)
