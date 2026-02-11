import sys
from pathlib import Path

import streamlit as st
import requests


project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import (
    LOGIN_API_ENDPOINT,
    REGISTER_API_ENDPOINT,
    LOGOUT_API_ENDPOINT,
    MESSAGE_SEND_ENDPOINT,
    MESSAGE_LIST_ENDPOINT,
    CONVERSATION_LIST_ENDPOINT,
    CONVERSATION_UPDATE_ENDPOINT,
    CONVERSATION_DELETE_ENDPOINT,
    RATE_LIMIT_STATUS_ENDPOINT
)

st.set_page_config(page_title="Movie Recommendations", page_icon="🎬")

welcome_message = "Hi! I can help you find movies by mood, genre, or vibe. "
MAX_USER_MESSAGE_LEN = 2000


default_values = {
    "logged_in": False, 
    "username": None,
    "user_id": None,
    "conversation_id": None,
    "is_new_user": False,
    "access_token": None,
    "messages": [],
    "conversations": [],
    "show_rate_limits": False
}

for key, value in default_values.items():
    if key not in st.session_state:
        st.session_state[key] = value

# -- helpers --


def fetch_conversations():
    """
    Fetch all conversations for the logged-in user.
    User is authenticated via JWT token in Authorization header.
    """
    if not st.session_state.access_token:
        return []
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        r = requests.get(CONVERSATION_LIST_ENDPOINT, headers=headers)
        
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"Failed to fetch conversations: {r.json().get('detail', r.text)}")
            return []
    except Exception as e:
        st.error(f"Error fetching conversations: {e}")
        return []
    
def load_conversation(conversation_id: int):
    """Load messages from a selected conversation, newest first."""
    if not st.session_state.access_token:
        return []

    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        url = MESSAGE_LIST_ENDPOINT.replace("{id}", str(conversation_id))
        params = {"limit": 0}  # all messages

        r = requests.get(url, headers=headers, params=params)

        if r.status_code == 200:
            messages = r.json()
            # Keep newest message first (no reversing)
            st.session_state.messages = prepend_welcome_message([
                {"role": msg["role"], "content": msg["content"]} for msg in messages
            ])
            st.session_state.conversation_id = conversation_id
        else:
            st.error(f"Failed to load conversation: {r.text}")

    except Exception as e:
        st.error(f"Error loading conversation: {e}")

def start_new_chat():
    st.session_state.messages = prepend_welcome_message([])
    st.session_state.conversation_id = None

def rename_conversation(conversation_id: int, new_title: str):
    """Rename a conversation and update in database."""
    if not st.session_state.access_token:
        st.error("Not authenticated")
        return
    if not new_title.strip():
        st.error("Title cannot be empty")
        return
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        url = CONVERSATION_UPDATE_ENDPOINT.replace("{id}", str(conversation_id))
        payload = {"title": new_title.strip()}
        r = requests.patch(url, json=payload, headers=headers)
        if r.status_code == 200:
            st.session_state.conversations = fetch_conversations()
            st.success(f"Conversation renamed to '{new_title}'")
        else:
            st.error(f"Failed to rename conversation: {r.json().get('detail', r.text)}")
    except Exception as e:
        st.error(f"Error renaming conversation: {e}")

def delete_conversation_by_id(conversation_id: int):
    """Delete a conversation from the database."""
    if not st.session_state.access_token:
        st.error("Not authenticated")
        return
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        url = CONVERSATION_DELETE_ENDPOINT.replace("{id}", str(conversation_id))
        r = requests.delete(url, headers=headers)
        if r.status_code == 200:
            # Clear current conversation if we deleted it
            if st.session_state.conversation_id == conversation_id:
                st.session_state.conversation_id = None
                st.session_state.messages = []
            st.session_state.conversations = fetch_conversations()
            st.success("Conversation deleted successfully")
        else:
            st.error(f"Failed to delete conversation: {r.json().get('detail', r.text)}")
    except Exception as e:
        st.error(f"Error deleting conversation: {e}")


def request_delete_conversation(conversation_id: int):
    """Stage a conversation for deletion confirmation."""
    st.session_state.pending_delete_conversation_id = conversation_id


def clear_delete_confirmation():
    """Clear any pending delete confirmation."""
    st.session_state.pending_delete_conversation_id = None


def login(username:str, password:str):
    try:
        r = requests.post(LOGIN_API_ENDPOINT, json={
            "username": username,
            "password": password
        })
        if r.status_code == 200:
            data = r.json()
            st.session_state.logged_in = True
            st.session_state.is_new_user = False
            st.session_state.access_token = data.get("access_token")
            st.rerun()
        else:
            st.error(r.json().get("detail", "Login failed"))
    except Exception as e:
        st.error(f"Login error: {e}")


def register(username:str, password:str):
    try:
        r = requests.post(REGISTER_API_ENDPOINT, json={
            "username": username,
            "password": password
        })
        if r.status_code in (200, 201):
            data = r.json()
            st.session_state.logged_in = True
            st.session_state.is_new_user = True
            st.session_state.access_token = data.get("access_token")
            st.success("Account created!")
            st.rerun()
        else:
            st.error(r.json().get("detail", "Registration failed"))
    except Exception as e:
        st.error(f"Registration error: {e}")


def logout():
    try:
        headers = {}
        if st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"

        requests.post(LOGOUT_API_ENDPOINT, headers=headers)
    except:
        pass  # even if API fails, we clear local state

    st.session_state.logged_in = False
    st.session_state.user_id = None
    st.session_state.is_new_user = False
    st.session_state.access_token = None
    st.session_state.show_rate_limits = False

def fetch_rate_limit_status():
    """Fetch rate limit status for the current user."""
    if not st.session_state.access_token:
        st.error("Not authenticated")
        return None
    
    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        r = requests.get(RATE_LIMIT_STATUS_ENDPOINT, headers=headers)
        
        if r.status_code == 200:
            return r.json()
        else:
            st.error(f"Failed to fetch rate limit status: {r.json().get('detail', r.text)}")
            return None
    except Exception as e:
        st.error(f"Error fetching rate limit status: {e}")
        return None

def send_message(user_input: str, conversation_id: int | None):
    """
    Send a message to the backend. 
    Uses MESSAGE_SEND_ENDPOINT; conversation_id is optional.
    User is authenticated via JWT token.
    """
    headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    payload = {
        "conversation_id": conversation_id,
        "content": user_input, 
        "role": "user"
    }

    try:
        r = requests.post(MESSAGE_SEND_ENDPOINT, json=payload, headers=headers)

        if r.status_code in (200, 201):
            return r.json()
        else:
            st.error(f"Chat API error: {r.json().get('detail', r.text)}")
            return {"conversation_id": conversation_id, "assistant_message": "[Error]"}
    except Exception as e:
        st.error(f"Chat request failed: {e}")
        return {"conversation_id": conversation_id, "assistant_message": "[Error]"}


def sanitize_user_input(user_input: str) -> str:
    if user_input is None:
        return ""
    cleaned = user_input.strip()
    cleaned = "".join(ch for ch in cleaned if ch >= " " or ch in ("\n", "\t"))
    return cleaned


def format_italic_preview(message: str) -> str:
    escaped = (
        message
        .replace("\\", "\\\\")
        .replace("*", "\\*")
        .replace("_", "\\_")
        .replace("`", "\\`")
    )
    return f"*{escaped}*"


def prepend_welcome_message(messages: list[dict]) -> list[dict]:
    if messages and messages[0].get("role") == "assistant" and messages[0].get("content") == welcome_message:
        return messages
    return [{"role": "assistant", "content": welcome_message}] + messages


# -- page --

if not st.session_state.logged_in:
    st.title("🔐 Welcome")

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        st.subheader("Login")
        with st.form("login_form", clear_on_submit=False):
            login_user = st.text_input("Username", key="login_user")
            login_pass = st.text_input(
                "Password", type="password", key="login_pass")
            if st.form_submit_button("Login"):
                login(login_user, login_pass)

    with tab2:
        st.subheader("Register")
        with st.form("register_form", clear_on_submit=False):
            reg_user = st.text_input("Username", key="reg_user")
            reg_pass = st.text_input("Password", type="password", key="reg_pass")
            if st.form_submit_button("Register"):
                register(reg_user, reg_pass)

else:
    # Top right logout button + check limits button
    col1, col2, col3 = st.columns([0.7, 0.15, 0.15])
    with col1:
        st.title("💬 Movie Assistant")
    with col2:
        if st.button("📊 Limits", use_container_width=True, help="Check your rate limits"):
            st.session_state.show_rate_limits = not st.session_state.get("show_rate_limits", False)
    with col3:
        if st.button("Logout", use_container_width=True):
            logout()
    
    # Display rate limit status if toggled
    if st.session_state.get("show_rate_limits", False):
        st.divider()
        with st.container(border=True):
            st.subheader("⏱️ Rate Limit Status")
            stats = fetch_rate_limit_status()
            
            if stats:
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("**Per Minute**")
                    st.metric(
                        "Used",
                        f"{stats['requests_this_minute']}/{stats['minute_limit']}",
                        delta=f"{stats['minute_remaining']} remaining"
                    )
                    st.progress(
                        min(stats['requests_this_minute'] / stats['minute_limit'], 1.0),
                        text=f"{stats['minute_percentage']:.1f}%"
                    )
                
                with col_b:
                    st.write("**Per Hour**")
                    st.metric(
                        "Used",
                        f"{stats['requests_this_hour']}/{stats['hour_limit']}",
                        delta=f"{stats['hour_remaining']} remaining"
                    )
                    st.progress(
                        min(stats['requests_this_hour'] / stats['hour_limit'], 1.0),
                        text=f"{stats['hour_percentage']:.1f}%"
                    )
        st.divider()

    # Sidebar with conversations
    with st.sidebar:
        st.header("Conversations")
        st.button("➕ New Chat", on_click=start_new_chat, use_container_width=True)

        if "pending_delete_conversation_id" not in st.session_state:
            st.session_state.pending_delete_conversation_id = None

        # Fetch conversations once and store in session
        if not st.session_state.conversations:
            st.session_state.conversations = fetch_conversations()

        for conv in st.session_state.conversations:
            display_title = conv["title"] or f"Chat {conv['id']}"
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                if st.button(display_title, key=f"conv_{conv['id']}", use_container_width=True):
                    load_conversation(conv["id"])
            with col2:
                if st.button("✏️", key=f"edit_{conv['id']}"):
                    st.session_state[f"editing_conv_{conv['id']}"] = True
            with col3:
                if st.button("🗑️", key=f"delete_{conv['id']}"):
                    request_delete_conversation(conv["id"])
            
            # Show edit dialog if editing this conversation
            if st.session_state.get(f"editing_conv_{conv['id']}", False):
                new_title = st.text_input(
                    "New title:",
                    value=conv["title"] or "",
                    key=f"title_input_{conv['id']}"
                )
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Save", key=f"save_{conv['id']}"):
                        rename_conversation(conv["id"], new_title)
                        st.session_state[f"editing_conv_{conv['id']}"] = False
                        st.rerun()
                with col2:
                    if st.button("Cancel", key=f"cancel_{conv['id']}"):
                        st.session_state[f"editing_conv_{conv['id']}"] = False
                        st.rerun()

            if st.session_state.pending_delete_conversation_id == conv["id"]:
                st.warning("Delete this conversation?")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Confirm", key=f"confirm_delete_{conv['id']}"):
                        delete_conversation_by_id(conv["id"])
                        clear_delete_confirmation()
                        st.rerun()
                with col2:
                    if st.button("Cancel", key=f"cancel_delete_{conv['id']}"):
                        clear_delete_confirmation()
                        st.rerun()

    # Messages area
    # TODO make user messages right aligned and assistant messages left aligned
    if not st.session_state.messages and st.session_state.conversation_id is None:
        st.session_state.messages = prepend_welcome_message([])

    if st.session_state.messages:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.chat_message("user").text(msg["content"])
            else:
                st.chat_message("assistant").markdown(msg["content"])

    user_input = st.chat_input("Type your message...")
    if user_input:
        sanitized_input = sanitize_user_input(user_input)
        if not sanitized_input:
            st.warning("Please enter a message.")
            st.stop()
        if len(sanitized_input) > MAX_USER_MESSAGE_LEN:
            st.warning(f"Message too long (max {MAX_USER_MESSAGE_LEN} characters).")
            st.stop()

        # Show user message immediately (italic preview)
        st.chat_message("user").markdown(format_italic_preview(sanitized_input))

        assistant_placeholder = st.empty()
        assistant_placeholder.chat_message("assistant").markdown("_Thinking..._")

        # Send message to backend
        with st.spinner("Getting recommendations..."):
            bot_response = send_message(sanitized_input, st.session_state.conversation_id)

        # Update conversation_id if it's a new conversation
        st.session_state.conversation_id = bot_response.get("conversation_id")

        # Refresh conversation list to update order by most recent message
        st.session_state.conversations = fetch_conversations()

        # Append user + assistant messages
        st.session_state.messages.append({"role": "user", "content": sanitized_input})
        assistant_message = bot_response.get("assistant_message")
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message
        })

        assistant_placeholder.chat_message("assistant").markdown(assistant_message)

        # Refresh UI
        st.rerun()