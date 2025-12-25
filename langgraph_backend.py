from langgraph.graph import START, StateGraph,END
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(model='llama-3.3-70b-versatile')
title_llm = ChatGroq(model='llama-3.3-70b-versatile',streaming=False)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage],add_messages]
    title: str

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm.invoke(messages)
    return {'messages':response}

def get_title(state:ChatState):
    human_message = state['messages'][-1].content
    prompt = f"Generate a logical title for the given message from the user's message {human_message}, I do not need a big paragraph keep it within 1 line and max 30 words"
    response = title_llm.invoke(prompt)
    return {'title':response.content}

def title_condition(state:ChatState)->Literal['chat_node','get_title']:
    if not state.get('title'):
        return 'get_title'
    else:
        return 'chat_node'

# checkpointer
checkpointer = InMemorySaver()

graph = StateGraph(ChatState)

graph.add_node('chat_node',chat_node)
graph.add_node('get_title',get_title)

# graph.add_edge(START,'chat_node')
graph.add_conditional_edges(START,title_condition)
graph.add_edge('get_title','chat_node')
graph.add_edge('chat_node',END)

chatbot = graph.compile(checkpointer=checkpointer)