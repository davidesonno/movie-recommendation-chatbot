# -- logging --

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult
from langchain_core.messages import ToolMessage

class LoggingHandler(BaseCallbackHandler):
    def on_llm_start(self, serialized, prompts, **kwargs) -> None:
        print(f"LLM call starting: {prompts[0][:100]}...")  # Log prompt start

    def on_llm_end(self, response: LLMResult, **kwargs) -> None:
        print(f"LLM response: {response.llm_output['token_usage']}")
    
    def on_tool_start(self, serialized, input_str, **kwargs) -> None:
        print(f"Tool `{serialized['name']}` starting with: {input_str}")

    def on_tool_end(self, output: ToolMessage, **kwargs) -> None:
        print(f"Tool result: {output.content}")
