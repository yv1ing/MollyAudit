import json
import os
import xml.etree.ElementTree as ET


rules_list = []

def extract_rules(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()

    rules = root.findall('.//{xmlns://www.fortifysoftware.com/schema/rules}StructuralRule')

    for rule in rules:
        rule_info = {}

        vuln_kingdom = rule.find('{xmlns://www.fortifysoftware.com/schema/rules}VulnKingdom')
        vuln_category = rule.find('{xmlns://www.fortifysoftware.com/schema/rules}VulnCategory')
        vuln_subcategory = rule.find('{xmlns://www.fortifysoftware.com/schema/rules}VulnSubcategory')
        predicate = rule.find('{xmlns://www.fortifysoftware.com/schema/rules}Predicate')

        rule_info['language'] = rule.get('language')

        if rule_info['language'] in ['c', 'cpp', 'go', 'php', 'jsp', 'java', 'python', 'javascript']:
            rule_info['vuln_kingdom'] = vuln_kingdom.text.replace('        ', ' ') if vuln_kingdom is not None else None
            rule_info['vuln_category'] = vuln_category.text.replace('        ', ' ') if vuln_category is not None else None
            rule_info['vuln_subcategory'] = vuln_subcategory.text.replace('        ', ' ') if vuln_subcategory is not None else None
            rule_info['predicate'] = predicate.text.replace('        ', ' ') if predicate is not None else None

            rules_list.append(rule_info)



def load_fortify_rules(src_path):
    for root, dirs, files in os.walk(src_path):
        for file_name in files:
            if file_name.endswith('.xml'):
                file_path = os.path.join(root, file_name)
                extract_rules(file_path)

    open('../../fortify_rules.json', 'w', encoding='utf-8').write(json.dumps(rules_list))

if __name__ == '__main__':
    load_fortify_rules(r'C:\Users\yvling\Desktop\data')