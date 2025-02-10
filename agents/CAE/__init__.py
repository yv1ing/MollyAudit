"""
===代码审计工程师===
用于分析具体的源代码，包括数据流、控制流等
"""
import json
import re
import uuid
import xml.etree.ElementTree as ET
from langchain_core.messages import SystemMessage
from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnableWithMessageHistory
from langchain_openai import ChatOpenAI
from langchain_community.chat_message_histories import ChatMessageHistory
from agents.CAE.prompt import CAE_SYSTEM_PROMPT, CAE_HUMAN_PROMPT
from logger import Logger


class CAE:
    def __init__(self, base_url, api_key, model, process_output_callback):
        # LLM配置
        self.llm = ChatOpenAI(base_url=base_url, api_key=api_key, model=model)
        self.session_id = uuid.uuid4().hex

        # 内存记忆
        self.max_history_length = 10
        self.history = ChatMessageHistory()

        # 提示词配置
        self.system_prompt = CAE_SYSTEM_PROMPT
        self.human_prompt = CAE_HUMAN_PROMPT

        # 日志器配置
        self.log = Logger(name='CAE', callback=process_output_callback)

    def audit(self, project_structure, project_module_division, result_output_callback, event):
        self.log.info('CAE开始审计项目代码')

        # 提示词模板
        self.llm_tmpl = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            MessagesPlaceholder(variable_name='history'),
            HumanMessagePromptTemplate.from_template(template=self.human_prompt),
        ])

        # 调用链配置
        self.raw_chain = self.llm_tmpl | self.llm
        self.llm_chain = RunnableWithMessageHistory(
            self.raw_chain,
            lambda session_id: self.history,
            input_messages_key='content',
            history_messages_key='history',
        )

        # 进入审计流程
        input_content = 'continue'
        while True:
            if event.is_set():
                return

            # 剔除更早的对话
            while len(self.history.messages) > self.max_history_length:
                self.history.messages.pop(0)

            try:
                # 获取当前输出
                input_dict = {
                    'content': input_content,
                    'history': self.history.messages,
                }

                config_dict = {
                    'configurable': {'session_id': self.session_id}
                }

                result = self.llm_chain.invoke(input_dict, config_dict)
                if event.is_set():
                    return

                # 解析动作指令
                if xml_match := re.search(r'<root>.*?</root>', result.content, re.DOTALL):
                    try:
                        xml_content = xml_match.group(0)
                        xml_content = re.sub(
                            r'(<content>)(.*?)(</content>)',
                            r'\1<![CDATA[\2]]>\3',
                            xml_content,
                            flags=re.DOTALL
                        )

                        root = ET.fromstring(xml_content)
                        action = root.find('action').text
                        content = root.find('content').text
                        if content and content.startswith('<![CDATA[') and content.endswith(']]>'):
                            content = content[9:-3]
                    except Exception as e:
                        self.log.error(f'CAE动作指令不合法：尝试纠正')
                        input_content = 'ILLEGAL OUTPUT'
                        continue

                    # 执行动作
                    try:
                        if action == 'QUERY STRUCTURE':
                            self.log.info('CAE请求查询项目结构')
                            input_content = project_structure
                            continue

                        elif action == 'MODULE DIVISION':
                            self.log.info('CAE请求查询项目模块')
                            input_content = project_module_division
                            continue

                        elif action == 'QUERY SOURCE':
                            self.log.info(f'CAE请求查询源代码：{content}')
                            try:
                                input_content = open(content, 'r', encoding='utf-8').read()
                            except Exception as e:
                                input_content = str(e)
                            continue

                        elif action == 'OUTPUT RESULT':
                            self.log.warning('CAE输出代码审计结果')
                            dict_content = eval(content)
                            json_content = json.loads(json.dumps(dict_content))
                            output_content = f'漏洞类型：{json_content["漏洞类型"]}\n漏洞文件：{json_content["漏洞文件"]}\n相关代码：\n{json_content["相关代码"]}\n修复建议：\n{json_content["修复建议"]}\n'
                            result_output_callback(output_content)
                            input_content = 'continue'
                            continue

                        elif action == 'FINISH TASK':
                            self.log.info('CAE完成项目代码审计')
                            return

                        else:
                            self.log.error(f'CAE动作指令未定义：{action}')
                            return

                    except Exception as e:
                        self.log.error(e)
                        continue

            except Exception as e:
                self.log.error(e)
                continue
