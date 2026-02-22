import streamlit as st
from langgraph_tool_backend import chatbot, retreive_all_threads
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
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
    # Add user message to history
    st.session_state["message_history"].append(
        {"role": "user", "content": user_input}
    )

    with st.chat_message("user"):
        st.text(user_input)

    # Assistant streaming block
    with st.chat_message("assistant"):

        status_holder = {"box": None}
        tools_used = []  # Store unique tools used in this response

        def ai_only_stream():
            for message_chunk, metadata in chatbot.stream(
                {"messages": [HumanMessage(content=user_input)]},
                config=CONFIG,
                stream_mode="messages",
            ):

                # Detect tool execution
                if isinstance(message_chunk, ToolMessage):
                    tool_name = getattr(message_chunk, "name", "tool")

                    # Avoid duplicate entries
                    if tool_name not in tools_used:
                        tools_used.append(tool_name)

                    # Build cumulative label
                    label_text = "🔧 Tools used:\n" + "\n".join(
                        f"- `{t}`" for t in tools_used
                    )

                    # Create or update status box
                    if status_holder["box"] is None:
                        status_holder["box"] = st.status(
                            label_text,
                            expanded=True,
                        )
                    else:
                        status_holder["box"].update(
                            label=label_text,
                            state="running",
                            expanded=True,
                        )

                # Stream only assistant tokens
                if isinstance(message_chunk, AIMessage):
                    if message_chunk.content:
                        yield message_chunk.content

        # Stream assistant response
        ai_message = st.write_stream(ai_only_stream())

        # Finalize tool box (if any tools were used)
        if status_holder["box"] is not None:
            final_label = "✅ Tools used:\n" + "\n".join(
                f"- `{t}`" for t in tools_used
            )

            status_holder["box"].update(
                label=final_label,
                state="complete",
                expanded=False,
            )

    # Save assistant message to history
    st.session_state["message_history"].append(
        {"role": "assistant", "content": ai_message}
    )