from langchain_core.callbacks import BaseCallbackHandler


class CustomCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.temp_content = ''

    def on_llm_new_token(self, token: str, **kwargs) -> None:
        self.temp_content += token

    def on_llm_end(self, response, **kwargs):
        pass

