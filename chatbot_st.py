import streamlit as st
import requests
import uuid

st.title("Chatbot Shop Hoa Tươi My My🌸")

if "conversation" not in st.session_state:
    conversation_id = str(uuid.uuid4())
    st.session_state.conversation = {
        "session_id": conversation_id,
        "chat_history": []
    }

conversation = st.session_state.conversation


for message in conversation["chat_history"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


if prompt := st.chat_input("Bạn cần tư vấn sản phẩm gì không?"):
    # Add user message to chat history
    conversation["chat_history"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    payload = {
        "query": prompt,
        "sessionID": conversation["session_id"]
    }

    # Send the POST request to the Flask API
    response = requests.post("http://localhost:5000/api/chat", json=payload)

    if response.status_code == 200:
        api_response = response.json()
        st.markdown(api_response['content'])
        conversation["chat_history"].append({"role": "assistant", "content": api_response['content']})
    else:
        st.error(f"Error: {response.status_code}")
