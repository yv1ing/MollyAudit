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

from audit.rules import FROTIFY_RULES
from logger import Logger
from audit import callback
from audit.prompt import SYSTEM_PROMPT
from audit.language import LANGUAGE

xml_pattern = r'<root>.*?</root>'


class Audit:
    def __init__(self, base_url, api_key, reasoning_model, embedding_model, process_output_callback, result_output_callback):
        self.raw_chain = None
        self.source_files_list = []
        self.max_token = 4096
        self.reasoning_model = reasoning_model
        self.embedding_model = embedding_model
        self.fortify_rules = FROTIFY_RULES
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
        if len(self.source_files_list) <= 0:
            self.log.error('没有找到源代码文件')
            return

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
                    root = ET.fromstring(xml_content)

                    action = root.find('action').text
                    content = root.find('content').text
                except Exception as e:
                    print(result)
                    print(e)
                    self.log.error(f'动作指令不合法，尝试纠正')
                    input_content = 'ILLEGAL OUTPUT'
                    continue

                if action == 'QUERY STRUCTURE':
                    self.log.info('请求查询项目结构')
                    input_content = '\n'.join(x for x in self.source_files_list)
                    continue
                elif action == 'QUERY SOURCE':
                    self.log.info(f'请求查询源代码：{content}')
                    input_content = open(content, 'r', encoding='utf-8').read()
                    continue
                elif action == 'QUERY FORTIFY':
                    self.log.info(f'请求查询规则库：{content}')
                    input_content = '\n'.join(x for x in self.fortify_rules if x == content)
                    continue
                elif action == 'OUTPUT RESULT':
                    self.log.warning('输出代码审计结果')
                    self.result_output_callback(content)
                    self.store_messages_in_faiss(content)
                    input_content = 'ok'
                    continue
                elif action == 'FINISH TASK':
                    self.log.info('代码审计任务已完成')
                    return
                else:
                    self.log.error(f'动作指令未定义：{action}')
                    return

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
        self.log.info(f"代码审计结果已缓存，文档编号：{doc_id}")

    def load_source_files(self, path, lang):
        if lang in LANGUAGE:
            suffixes = LANGUAGE[lang]
        else:
            self.log.error('不支持的编程语言')
            return

        for root, _, files in os.walk(path):
            self.source_files_list.extend(
                os.path.join(root, file).replace('\\', '/') for file in files if any(file.endswith(suffix) for suffix in suffixes)
            )

        self.log.info(f'源代码文件加载完成，共：{len(self.source_files_list)} 个')
