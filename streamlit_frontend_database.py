import streamlit as st
from langgraph_database_backend import chatbot, retreive_all_threads
from langchain_core.messages import HumanMessage
import uuid

#***************************************Utility functions***************************************************************
def generate_thread_id():
    thread_id = uuid.uuid4()
    return thread_id

def reset_chat():
    """ Called when we click on new chat to get a fresh session"""
    thread_id = generate_thread_id()
    st.session_state['thread_id'] = thread_id
    add_thread(st.session_state['thread_id'])
    st.session_state['message_history'] = []

def add_thread(thread_id):
    ## Adds Thread IDs to the session's thread id list
    if thread_id not in st.session_state['chat_threads']:
        st.session_state['chat_threads'].append(thread_id)

def add_title(thread_id):
    try:
        return chatbot.get_state(config={'configurable':{'thread_id':thread_id}}).values['title']
    except:
        return str(thread_id)

def load_conversation(thread_id):
    try:
        return chatbot.get_state(config={'configurable':{'thread_id':thread_id}}).values['messages']
    except:
        return []

#*****************************************Session Creation************************************************************
if 'message_history' not in st.session_state:
    st.session_state['message_history'] = []

if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = generate_thread_id()

if 'chat_threads' not in st.session_state:
    st.session_state['chat_threads'] = retreive_all_threads()

add_thread(st.session_state['thread_id'])

CONFIG = {'configurable':{'thread_id':st.session_state['thread_id']}}

#*****************************************SideBar UI************************************************************
st.sidebar.title('Langgraph Chatbot')
if st.sidebar.button('New Chat'):
    reset_chat()

st.sidebar.header('My Conversations')
for thread_id in st.session_state['chat_threads'][::-1]:
    if st.sidebar.button(str(add_title(thread_id))):
        st.session_state['thread_id'] = thread_id
        messages = load_conversation(thread_id)

        temp_messages = []
        for msg in messages:
            if isinstance(msg,HumanMessage):
                role = 'user'
            else:
                role = 'assistant'
            temp_messages.append({'role':role,'content':msg.content})
        st.session_state['message_history'] = temp_messages

#*****************************************Main UI************************************************************

# Display the old messages
for message in st.session_state['message_history']:
    with st.chat_message(message['role']):
        st.text(message['content'])

# Get the new input
user_input = st.chat_input('Type Here')

# Generate the chat messages
if user_input:
    ## Add the message to message history
    st.session_state['message_history'].append({'role':'user','content':user_input})
    with st.chat_message('user'):
        st.text(user_input)

    ## Add the message to message history
    # st.session_state['message_history'].append({'role':'assistant','content':ai_message})
    with st.chat_message('assistant'):
        ai_message = st.write_stream(
            message_chunk.content for message_chunk, metadata in chatbot.stream(
                {'messages':[HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode='messages')
                )
    ## Add the message to message history
    st.session_state['message_history'].append({'role':'assistant','content':ai_message})