from langchain_openai import ChatOpenAI
from typing import List, Dict

from src.services.agent.agent_handler import AgentHandler
from src.services.agent.langchain.callbacks import LoggingHandler
from src.services.agent.langchain.tools import (
    UserContext, 
    get_preferences_tool, 
    upsert_preferences_tool, 
    recomend_movies,
    brave_search_tool
)
from src.services.agent.langchain.middleware import (
    LLMSafetyMiddleware,
    GreetingMiddleware,
    ToolErrorMiddleware
)

from langchain_core.messages import ToolMessage, AIMessage
from langchain.agents import create_agent

class LangChainAgentHandler(AgentHandler):

    DEBUG = False
    LOGGING = True

    def __init__(
        self,
        config: dict = {},
        llm_config: dict = {},
        preferences_db_config: dict = {},
    ) -> None:
        super().__init__(config, llm_config, preferences_db_config)

        provider = llm_config.get("PROVIDER", "none").upper()
        if provider in ("OPENAI", "GROQ"):
            self.llm = ChatOpenAI(
                model=llm_config.get("MODEL"),
                api_key=llm_config.get("PROVIDER_API_KEY"),
                base_url=llm_config.get("PROVIDER_BASE_URL"),
                temperature=0.7,
            )
        else:
            raise RuntimeError(f"Unsupported LLM provider: {provider}")
        
        GET_PREFERENCES = True
        UPDATE_PREFERENCES = True
        MOVIE_RAG = True
        WEB_SEARCH = True
        try:
            search = config.get("AGENT_WEB_SEARCH", False)
            key = config.get("BRAVE_SEARCH_API_KEY", None)
            if search and key:
                WEB_SEARCH = True
            else:
                print("Web search tool disabled due to missing configuration.")
        except: pass

        SYSTEM_PROMPT = (
        "You are a concise movie assistant. You chat about films, answer movie questions, and give recommendations when helpful."
        "Only recommend movies when it clearly helps the user or they ask for recommendations. Keep answers short and practical, with brief reasons for recommendations."
        "If you recommend a movie, include its description. "
        "- Use user preferences only for personalization when relevant."
        "- Update preferences only when the user gives explicit, unambiguous new info."
        "Use tools sparingly and only when they materially improve the answer. Limit:"
        "- Use movie retrieval only for facts or titles you don’t reliably know."
        "- Use retrieval filters if and only if the user asked for a specific movie genre/director/etc."
        "- Use web search if the user asks for even more details about a movie."
        "Prefer the conversation context and local data over external calls. If the user asks for something outside movies, politely refuse and steer back to movies."
        ).strip()

        self.tools = []
        if GET_PREFERENCES:
            self.tools.append(get_preferences_tool)
        if UPDATE_PREFERENCES:
            self.tools.append(upsert_preferences_tool)
        if MOVIE_RAG:
            self.tools.append(recomend_movies)
        if WEB_SEARCH:
            self.tools.append(brave_search_tool)

        self.middleware = [
            LLMSafetyMiddleware(self.llm),
            GreetingMiddleware(self.llm),
            ToolErrorMiddleware(),
        ]

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=SYSTEM_PROMPT,
            middleware=self.middleware,
            context_schema=UserContext,
            store=self._agent_store,
            debug=self.DEBUG,
        )

    def process_message(
        self,
        user_id: int,
        history: List[Dict],
    ) -> str:
        try:
            if not history:
                raise ValueError("History cannot be empty")
            
            # TODO maybe prepend to the histroy instead of appending
            prev_tool_outputs = self._agent_store.get("tools_output", user_id) or []
            if prev_tool_outputs:
                tool_output_summary = "\n".join([f"{i+1}. {to['tool_name']}: {to['content']}" for i, to in enumerate(prev_tool_outputs)])
                history.append({"role": "system", "content": f"Previous tool calls in this conversation:\n{tool_output_summary}"})
            
            # print("Invoking agent with history:", history)
            agent_response = self.agent.invoke(
                {"messages": history},
                context=UserContext(user_id=user_id),
                config={"callbacks": [LoggingHandler()]} if self.LOGGING else None
            )
            # print("Agent response:", agent_response)

            response_messages = agent_response.get("messages", [])
            last_message = response_messages[-1] if response_messages else {}
            last_message_content = last_message.content
            # print("Last message content:", last_message_content)

            last_message_content = None
            for msg in reversed(response_messages):
                if isinstance(msg, AIMessage) and msg.content.strip():
                    last_message_content = msg.content
                    break

            if not last_message_content:
                raise ValueError("Agent did not return any content in the response messages.")


            tool_messages = []
            for msg in response_messages:
                if isinstance(msg, ToolMessage):
                    tool_messages.append({
                        "tool_name": msg.name,
                        "content": msg.content
                    })

            # print(f"Tool calls: {tool_messages}")
            for tm in tool_messages:
                self._agent_store.put("tools_output", user_id, tm)


            return last_message_content
        except Exception as e:
            from datetime import datetime
            print(f"Error processing message with agent at time {datetime.now()}: {e}")
            return "Sorry, I had trouble processing your request. Please try again."
