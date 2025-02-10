import os
import logger
from app.constants import SUPPORT_LANGUAGE


def clean_tree(node, suffixes):
    sub_keys_to_remove = []
    for key, value in node.items():
        if key == 'files':
            continue
        elif isinstance(value, dict):
            clean_tree(value, suffixes)
            has_valid_content = 'files' in value or any(isinstance(sub_val, dict) and sub_val for sub_val in value.values())
            if not has_valid_content:
                sub_keys_to_remove.append(key)

    for key in sub_keys_to_remove:
        del node[key]

    if all(key == 'files' for key in node) and ('files' not in node or not node['files']):
        node.clear()


def print_tree(tree):
    formatted_str = ''
    formatted = format_tree(tree)

    for line in formatted:
        formatted_str += f"{line}\n"

    return formatted_str


def format_tree(node, level=0):
    result = []
    indent = '  ' * level

    for key, value in node.items():
        if key == 'files':
            for file in value:
                result.append(f"{indent}- {file}")
        else:
            result.append(f"{indent}- {key}/")

            if isinstance(value, dict):
                result.extend(format_tree(value, level + 1))

    return result


def build_directory_tree(path, lang, callback):
    log = logger.Logger('app', callback=callback)

    if lang in SUPPORT_LANGUAGE:
        suffixes = SUPPORT_LANGUAGE[lang]
    else:
        log.error(f'不支持的语言：{lang}')
        return

    absolute_path = os.path.abspath(path).replace('\\', '/')
    src_files = []
    tree = {absolute_path: {}}

    for root, _, files in os.walk(absolute_path):
        relative_path = os.path.relpath(root, absolute_path)
        current_node = tree[absolute_path]

        if relative_path != '.':
            parts = relative_path.split(os.sep)
            for part in parts:
                if part not in current_node:
                    current_node[part] = {}
                current_node = current_node[part]

        for suffix in suffixes:
            lang_files = [file for file in files if file.endswith(suffix)]
            if lang_files:
                if 'files' not in current_node:
                    current_node['files'] = []
                current_node['files'].extend(lang_files)
                src_files.extend(lang_files)

    if len(src_files) > 0:
        clean_tree(tree[absolute_path], suffixes)
        return print_tree(tree)
    else:
        return None
