import datetime
from dotenv import load_dotenv


from typing import Annotated, Callable
from typing_extensions import TypedDict

from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, AIMessage
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.graph import StateGraph, START, END
from langchain_core.runnables import RunnableConfig

load_dotenv()


def make_prompt(base_system_prompt: str) -> Callable[[dict, RunnableConfig], list]:
    def prompt(state: dict, config: RunnableConfig) -> list:
        user_id = config["configurable"].get("user_id")
        global_state = config["configurable"].get("global_state")

        system_prompt = (
            base_system_prompt
            + f"\n\nUser's active reservation: no is active \n"
            + f"Today is: {datetime.datetime.now()}"
        )

        print("global state", global_state)
        print("state", state)

        return [{"role": "system", "content": system_prompt}] + state["messages"]

    return prompt


tools = []
llm = ChatOpenAI(model="gpt-4o")


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    is_complete: bool


agent_form = create_react_agent(
    model=llm,
    tools=tools,
    prompt=make_prompt("Eres un asistente de agendamiento de vuelos"),
    name="flight_assistant",
)

canvas = StateGraph(State)

llm = ChatOpenAI(model="gpt-4o")


def chatbot(state: State):

    messages = state["messages"]
    state["is_complete"] = False

    chat_bot_response = agent_form.invoke(
        {"messages": messages},
        {
            "configurable": {
                "global_state": state,
            }
        },
    )
    result = chat_bot_response["messages"][-1].content

    updated_messages = messages + [AIMessage(content=result)]

    return {"messages": updated_messages}


canvas.add_node("chatbot", chatbot)

canvas.add_edge(START, "chatbot")
canvas.add_edge("chatbot", END)

graph = canvas.compile()


def stream_graph_updates(user_input: str):
    for event in graph.stream({"messages": [{"role": "user", "content": user_input}]}):
        for value in event.values():
            print("Assistant:", value["messages"][-1].content)
