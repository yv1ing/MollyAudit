import os
import warnings
import logger
from agents.CAE import CAE
from agents.CSA import CSA
from utils import build_directory_tree

warnings.simplefilter('ignore', FutureWarning)

home_dir = os.path.expanduser("~")
config_file_name = ".mollyaudit"
config_file_path = os.path.join(home_dir, config_file_name)

GLOBAL_CONFIG = {
    "base_url": "https://openai.com/v1",
    "api_key": "",
    "csa_model": "gpt-4o",
    "cae_model": "o3-mini-all",
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


def real_update_config(key, value):
    global GLOBAL_CONFIG

    GLOBAL_CONFIG[key] = value
    with open(config_file_path, 'w') as file:
        for k, v in GLOBAL_CONFIG.items():
            file.write(f"{k}={v}\n")


def audit_code(base_url, api_key, src_root, language, cae_model, csa_model, process_output_callback,
               result_output_callback, event):
    log = logger.Logger('app', process_output_callback)

    csa = CSA(base_url=base_url, api_key=api_key, model=csa_model, process_output_callback=process_output_callback)
    cae = CAE(base_url=base_url, api_key=api_key, model=cae_model, process_output_callback=process_output_callback)

    project_structure = build_directory_tree(src_root, language, process_output_callback)
    if project_structure is None:
        log.error('未找到源代码文件')
        return

    project_module_division = csa.analyse(project_structure=project_structure)
    cae.audit(project_structure=project_structure, project_module_division=project_module_division, event=event,
              result_output_callback=result_output_callback)
