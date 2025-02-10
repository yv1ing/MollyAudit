"""
===软件架构师===
用于分析项目的整体框架，抽取出清晰的项目结构和功能划分
"""
from langchain_core.messages import SystemMessage
from langchain_core.prompts import HumanMessagePromptTemplate, ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from agents.CSA.prompt import CSA_SYSTEM_PROMPT, CSA_HUMAN_PROMPT
from logger import Logger


class CSA:
    def __init__(self, base_url, api_key, model, process_output_callback):
        # LLM配置
        self.llm = ChatOpenAI(base_url=base_url, api_key=api_key, model=model)

        # 提示词配置
        self.system_prompt = CSA_SYSTEM_PROMPT
        self.human_prompt = CSA_HUMAN_PROMPT

        # 日志器配置
        self.log = Logger(name='CSA', callback=process_output_callback)


    def analyse(self, project_structure):
        self.log.info('CSA开始分析项目模块')

        # 提示词模板
        self.llm_tmpl = ChatPromptTemplate.from_messages([
            SystemMessage(content=self.system_prompt),
            HumanMessagePromptTemplate.from_template(template=self.human_prompt),
        ])

        # 调用链配置
        self.llm_chain = self.llm_tmpl | self.llm

        # 获取分析结果
        with get_openai_callback() as cb:
            result = self.llm_chain.invoke({'project_structure': project_structure})

            # TODO: 接入token用量统计
            # print(f"请求消耗的输入 token 数: {cb.prompt_tokens}")
            # print(f"请求消耗的输出 token 数: {cb.completion_tokens}")
            # print(f"请求总共消耗的 token 数: {cb.total_tokens}")

        self.log.info('CSA完成分析项目模块')
        return result.content
