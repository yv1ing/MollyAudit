import os
import re
import time
import uuid
import xml.etree.ElementTree as ET
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory

from logger import Logger
from audit import callback
from audit.prompt import SYSTEM_PROMPT

reasoning_model = 'gemini-2.0-flash-thinking-exp'
embedding_model = 'text-embedding-3-large'

xml_pattern = r'<root>.*?</root>'


class Audit:
    def __init__(self):
        self.raw_chain = None
        self.source_files_list = []
        self.chat_history = ChatMessageHistory()
        self.session_id = uuid.uuid4().hex
        self.response_callback = callback.CustomCallbackHandler()
        self.embedding = OpenAIEmbeddings(model=embedding_model)
        self.llm = ChatOpenAI(model=reasoning_model, streaming=True, callbacks=[self.response_callback])
        self.log = Logger('audit')
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name='messages'),
            ('human', '{input}'),
        ])

    def audit(self, callback_function):
        self.log.info('Start auditing')

        input_content = ''
        while True:
            time.sleep(3)
            result = self.send_message(input_content)
            xml_match = re.search(xml_pattern, result, re.DOTALL)

            if xml_match:
                xml_content = xml_match.group(0)
                root = ET.fromstring(xml_content)

                action = root.find('action').text
                content = root.find('content').text

                if action == 'QUERY STRUCTURE':
                    self.log.info('Request to query project structure')
                    input_content = '\n'.join(x for x in self.source_files_list)
                    continue
                elif action == 'QUERY SOURCE':
                    self.log.info(f'Request source code: {content}')
                    input_content = open(content, 'r', encoding='utf-8').read()
                    continue
                elif action == 'OUTPUT RESULT':
                    self.log.warning(f'Audit result: \n{content}\n')
                    callback_function(content)  # Callback function, used to obtain results externally
                    input_content = ''
                    continue
                else:
                    self.log.critical(f'Unknown action! {action}')
                    break

    def send_message(self, input_content):
        self.response_callback.temp_content = ''

        if input_content == '':
            input_content = 'nothing'

        input_dict = {
            'input': input_content,
            'context': '',
        }
        config_dict = {
            'configurable': {'session_id': self.session_id}
        }

        self.raw_chain = self.prompt | self.llm
        chain_with_message_history = RunnableWithMessageHistory(
            self.raw_chain,
            lambda session_id: self.chat_history,
            input_messages_key='input',
            history_messages_key='messages',
        )

        for _ in chain_with_message_history.stream(input_dict, config_dict):
            pass

        return self.response_callback.temp_content

    def load_source_files(self, path, language):
        self.log.info('Loading source files')

        if language == 'php':
            suffixes = ['.php', '.php3', 'php4', 'php5']
        elif language == 'python':
            suffixes = ['.py']
        elif language == 'java':
            suffixes = ['.java']
        elif language == 'c':
            suffixes = ['.c']
        elif language == 'c++':
            suffixes = ['.cpp', 'cc']
        elif language == 'javascript':
            suffixes = ['.js']
        elif language == 'go':
            suffixes = ['.go']
        else:
            self.log.critical('Language not supported!')
            return

        for root, dirs, files in os.walk(path):
            for file_name in files:
                hit = False
                for suffix in suffixes:
                    if file_name.endswith(suffix):
                        hit = True
                        break

                if hit:
                    self.source_files_list.append(os.path.join(root, file_name))

        self.log.info(f'Finished loading source files. total files: {len(self.source_files_list)}')
