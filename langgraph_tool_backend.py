from langgraph.graph import START, StateGraph,END
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_groq import ChatGroq
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool
from dotenv import load_dotenv

import sqlite3
import requests
import os

load_dotenv()
ALPHA_VANTAGE_API = os.getenv("ALPHA_VANTAGE_API")


# Get Tools
# tools
search_tool = DuckDuckGoSearchRun(region='us-en')

# @tool
def calculator(first_num:float, second_num:float, operation:str)->dict:
    """ Performs basic arithmatic operation between two numbers.
    Supported operations: add, sub, mul, div"""
    try:
        if operation == 'add':
            result = first_num + second_num
        elif operation == 'sub':
            result = first_num - second_num
        elif operation =='mul':
            result = first_num * second_num
        elif operation == 'div':
            if second_num == 0:
                return {'error':'Division by 0 is not allowed'}
            result = first_num/second_num
        else:
            return {'error': f'Unsupported operation {operation}'}
        return {'first_num':first_num, 'second_num':second_num, 'operation':operation, 'result':result}
    except Exception as e:
        return {'error':str(e)}
    
@tool
def get_stock_price(symbol:str)->dict:
    """Fetch latest stock price for a given symbol (eg. 'AAPL', 'TSLA' etc.
    Keep the symbols consistent as we have in it in the stock market currently)
    using alpha vantage API key in the url"""
    url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}&apikey={ALPHA_VANTAGE_API}"
    r = requests.get(url)
    return r.json()

tools = [search_tool, calculator, get_stock_price]

# LLMs
llm = ChatGroq(model='llama-3.3-70b-versatile')
title_llm = ChatGroq(model='llama-3.3-70b-versatile',streaming=False)
llm_with_tool = llm.bind_tools(tools)

class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage],add_messages]
    title: str

def chat_node(state: ChatState):
    messages = state['messages']
    response = llm_with_tool.invoke(messages)
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

tool_node = ToolNode(tools)

# checkpointer
conn = sqlite3.connect(database='chatbot.db',check_same_thread=False)
checkpointer = SqliteSaver(conn=conn)

graph = StateGraph(ChatState)

graph.add_node('chat_node',chat_node)
graph.add_node('get_title',get_title)
graph.add_node('tools',tool_node)

# graph.add_edge(START,'chat_node')
graph.add_conditional_edges(START,title_condition)
graph.add_edge('get_title','chat_node')
graph.add_conditional_edges('chat_node',tools_condition)
graph.add_edge('tools','chat_node')

chatbot = graph.compile(checkpointer=checkpointer)

def retreive_all_threads():
    all_threads = set()
    for checkpoints in checkpointer.list(None):
        all_threads.add(checkpoints.config['configurable']['thread_id'])
    return list(all_threads)