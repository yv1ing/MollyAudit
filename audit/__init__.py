import os
import re
import time
import uuid
import tiktoken
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

reasoning_model = 'gemini-2.0-flash-thinking-exp'
embedding_model = 'text-embedding-3-large'

xml_pattern = r'<root>.*?</root>'


class Audit:
    def __init__(self):
        self.raw_chain = None
        self.source_files_list = []
        self.max_token = 4096
        self.chat_history = ChatMessageHistory()
        self.session_id = uuid.uuid4().hex
        self.response_callback = callback.CustomCallbackHandler()
        self.embedding = OpenAIEmbeddings(model=embedding_model)
        self.llm = ChatOpenAI(
            model=reasoning_model,
            streaming=True,
            callbacks=[self.response_callback]
        )
        self.log = Logger('audit')
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

    def audit(self, callback_function):
        self.log.info('Start auditing')

        input_content = ''
        while True:
            result = self.send_message(input_content)

            if xml_match := re.search(xml_pattern, result, re.DOTALL):
                try:
                    xml_content = xml_match.group(0)
                    root = ET.fromstring(xml_content)

                    action = root.find('action').text
                    content = root.find('content').text
                except Exception as e:
                    self.log.error(f'Illegal output, try to correct')
                    input_content = 'ILLEGAL OUTPUT'
                    continue

                if action == 'QUERY STRUCTURE':
                    self.log.info('Request project structure')
                    input_content = '\n'.join(x for x in self.source_files_list)
                    continue
                elif action == 'QUERY SOURCE':
                    self.log.info(f'Request source code: {content}')
                    input_content = open(content, 'r', encoding='utf-8').read()
                    continue
                elif action == 'OUTPUT RESULT':
                    self.log.warning(f'Audit result: \n\n{content}')
                    self.store_messages_in_faiss(content)
                    callback_function(content)  # Callback function, used to obtain results externally
                    input_content = ''
                    continue
                else:
                    self.log.critical(f'Unknown action! {action}')
                    break

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

        self.log.debug(f'Chat messages: {input_dict}')

        for _ in chain_with_message_history.stream(input_dict, config_dict):
            pass

        return self.response_callback.temp_content

    def store_messages_in_faiss(self, message):
        text_embedding = self.embedding.embed_query(message)
        doc_id = str(uuid.uuid4())
        self.messages_db.add_embeddings([(doc_id, text_embedding)], metadatas=[{"id": doc_id}])
        self.log.info(f"Audit result stored in messages_db with ID: {doc_id}")

    def load_source_files(self, path, lang):
        self.log.info('Loading source files')

        if lang in LANGUAGE:
            suffixes = LANGUAGE[lang]
        else:
            self.log.critical('Language not supported!')
            return

        for root, _, files in os.walk(path):
            self.source_files_list.extend(
                os.path.join(root, file) for file in files if any(file.endswith(suffix) for suffix in suffixes)
            )

        self.log.info(f'Finished loading source files. total files: {len(self.source_files_list)}')
