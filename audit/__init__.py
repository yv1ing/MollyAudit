import json
import os
import re
import uuid
import xml.etree.ElementTree as ET
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import SystemMessage
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.vectorstores import FAISS
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain_community.document_transformers import EmbeddingsRedundantFilter
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import EmbeddingsFilter, DocumentCompressorPipeline
from langchain_text_splitters import CharacterTextSplitter
from logger import Logger
from audit import callback
from audit.prompt import SYSTEM_PROMPT
from audit.language import LANGUAGE

xml_pattern = r'<root>.*?</root>'


class Audit:
    def __init__(self, base_url, api_key, reasoning_model, embedding_model, process_output_callback,
                 result_output_callback):
        self.raw_chain = None
        self.directory_tree = None
        self.reasoning_model = reasoning_model
        self.embedding_model = embedding_model
        self.process_output_callback = process_output_callback
        self.result_output_callback = result_output_callback
        self.chat_history = ChatMessageHistory()
        self.session_id = uuid.uuid4().hex
        self.response_callback = callback.CustomCallbackHandler()
        self.embedding = OpenAIEmbeddings(
            base_url=base_url,
            api_key=api_key,
            model=embedding_model
        )
        self.llm = ChatOpenAI(
            base_url=base_url,
            api_key=api_key,
            model=reasoning_model,
            streaming=True,
            callbacks=[self.response_callback]
        )
        self.log = Logger('audit', callback=self.process_output_callback)
        self.splitter = CharacterTextSplitter(
            chunk_size=300,
            chunk_overlap=0,
            separator=". ",
        )
        self.messages_db = FAISS.from_texts(['nothing'], self.embedding)
        self.retriever = self.messages_db.as_retriever()
        self.redundant_filter = EmbeddingsRedundantFilter(embeddings=self.embedding)
        self.relevant_filter = EmbeddingsFilter(
            embeddings=self.embedding,
            similarity_threshold=0.76,
        )
        self.pipeline_compressor = DocumentCompressorPipeline(
            transformers=[self.splitter, self.redundant_filter, self.relevant_filter]
        )
        self.compression_retriever = ContextualCompressionRetriever(
            base_compressor=self.pipeline_compressor,
            base_retriever=self.retriever,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content=SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name='messages'),
            ('human', '{input}'),
        ])

    def audit(self, event):
        self.log.info('开始代码审计流程')
        self.log.info(f'当前推理模型：{self.reasoning_model}')
        self.log.info(f'当前嵌入模型：{self.embedding_model}')

        input_content = ''
        while True:
            if event.is_set():
                return

            try:
                result = self.send_message(input_content)
            except Exception as e:
                self.log.error(e)
                return

            if event.is_set():
                return

            if xml_match := re.search(xml_pattern, result, re.DOTALL):
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
                    print(result)
                    print(e)
                    self.log.error(f'动作指令不合法，尝试纠正')
                    input_content = 'ILLEGAL OUTPUT'
                    continue

                try:
                    if action == 'QUERY STRUCTURE':
                        self.log.info('请求查询项目结构')
                        input_content = self.print_tree(self.directory_tree)
                        self.store_messages_in_faiss(input_content)
                        continue
                    elif action == 'QUERY SOURCE':
                        self.log.info(f'请求查询源代码：{content}')
                        input_content = open(content, 'r', encoding='utf-8').read()
                        self.store_messages_in_faiss(input_content)
                        continue
                    elif action == 'OUTPUT RESULT':
                        self.log.warning('输出代码审计结果')
                        dict_content = eval(content)
                        json_content = json.loads(json.dumps(dict_content))
                        output_content = f'漏洞类型：{json_content["漏洞类型"]}\n漏洞文件：{json_content["漏洞文件"]}\n相关代码：\n{json_content["相关代码"]}\n修复建议：\n{json_content["修复建议"]}\n'
                        self.result_output_callback(output_content)
                        self.store_messages_in_faiss(output_content)
                        input_content = 'ok'
                        continue
                    elif action == 'FINISH TASK':
                        self.log.info('代码审计任务已完成')
                        return
                    else:
                        self.log.error(f'动作指令未定义：{action}')
                        return
                except Exception as e:
                    self.log.error(e)
                    continue

    def send_message(self, input_content):
        self.response_callback.temp_content = ''
        compressed_context = self.compression_retriever.invoke(input_content)

        if input_content == '':
            input_content = 'nothing'

        input_dict = {
            'input': input_content,
            'context': compressed_context,
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

    def store_messages_in_faiss(self, message):
        text_embedding = self.embedding.embed_query(message)
        doc_id = str(uuid.uuid4())
        self.messages_db.add_embeddings([(doc_id, text_embedding)], metadatas=[{"id": doc_id}])

    def build_directory_tree(self, path, lang):
        if lang in LANGUAGE:
            suffixes = LANGUAGE[lang]
        else:
            self.log.error(f'不支持的语言：{lang}')
            return

        absolute_path = os.path.abspath(path).replace('\\', '/')
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

        self.print_tree(tree)
        self.directory_tree = tree

    def format_tree(self, node, level=0):
        result = []
        indent = '  ' * level
        for key, value in node.items():
            if key == 'files':
                for file in value:
                    result.append(f"{indent}- {file}")
            else:
                result.append(f"{indent}- {key}/")
                if isinstance(value, dict):
                    result.extend(self.format_tree(value, level + 1))

        return result

    def print_tree(self, tree):
        formatted_str = ''
        formatted = self.format_tree(tree)
        for line in formatted:
            formatted_str += f"{line}\n"
            # print(line)

        return formatted_str
