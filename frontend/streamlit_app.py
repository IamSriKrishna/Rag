
import os

import requests
import streamlit as st
from dotenv import load_dotenv


load_dotenv()

API_BASE_URL = os.getenv("RAG_API_BASE_URL", "").rstrip("/")

st.set_page_config(
    page_title="Multi-Document RAG Chat",
    page_icon="📚",
    layout="wide",
)


# --------------------------------------------------
# Session state
# --------------------------------------------------

def initialize_state():
    defaults = {
        "access_token": None,
        "user": None,
        "messages": [],
        "conversation_id": None,
        "scope_key": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


initialize_state()


# --------------------------------------------------
# API client helpers
# --------------------------------------------------

def api_request(method, endpoint, **kwargs):
    if not API_BASE_URL:
        raise RuntimeError(
            "Set RAG_API_BASE_URL in your .env file."
        )

    headers = kwargs.pop("headers", {})

    token = st.session_state.access_token
    if token:
        headers["Authorization"] = f"Bearer {token}"

    response = requests.request(
        method=method,
        url=f"{API_BASE_URL}{endpoint}",
        headers=headers,
        timeout=120,
        **kwargs,
    )

    if not response.ok:
        try:
            detail = response.json().get(
                "detail", response.text
            )
        except ValueError:
            detail = response.text

        raise RuntimeError(
            f"API error ({response.status_code}): {detail}"
        )

    if response.status_code == 204:
        return None

    return response.json()


def clear_chat():
    st.session_state.messages = []
    st.session_state.conversation_id = None


# --------------------------------------------------
# Authentication
# --------------------------------------------------

def authentication_screen():
    st.title("📚 Multi-Document RAG Chat")
    st.caption(
        "Upload documents and ask questions across your files."
    )

    login_tab, register_tab = st.tabs(
        ["Login", "Create account"]
    )

    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input(
                "Password", type="password"
            )
            login_clicked = st.form_submit_button(
                "Login", use_container_width=True
            )

        if login_clicked:
            try:
                result = api_request(
                    "POST",
                    "/auth/login",
                    json={
                        "email": email,
                        "password": password,
                    },
                )

                st.session_state.access_token = (
                    result["access_token"]
                )

                st.session_state.user = api_request(
                    "GET", "/auth/me"
                )

                st.rerun()

            except Exception as exc:
                st.error(str(exc))

    with register_tab:
        with st.form("register_form"):
            tenant_name = st.text_input(
                "Organization name"
            )
            register_email = st.text_input(
                "Email", key="register_email"
            )
            register_password = st.text_input(
                "Password (minimum 12 characters)",
                type="password",
                key="register_password",
            )

            register_clicked = st.form_submit_button(
                "Create account",
                use_container_width=True,
            )

        if register_clicked:
            try:
                api_request(
                    "POST",
                    "/auth/register",
                    json={
                        "tenant_name": tenant_name,
                        "email": register_email,
                        "password": register_password,
                    },
                )

                st.success(
                    "Account created. Please log in."
                )

            except Exception as exc:
                st.error(str(exc))


# --------------------------------------------------
# Document management
# --------------------------------------------------

def load_documents():
    return api_request("GET", "/documents")


def upload_documents(uploaded_files):
    progress = st.progress(0)
    total = len(uploaded_files)

    for index, uploaded_file in enumerate(
        uploaded_files, start=1
    ):
        try:
            api_request(
                "POST",
                "/documents/upload",
                files={
                    "file": (
                        uploaded_file.name,
                        uploaded_file.getvalue(),
                        uploaded_file.type
                        or "application/pdf",
                    )
                },
            )

            st.success(
                f"Uploaded: {uploaded_file.name}"
            )

        except Exception as exc:
            st.error(
                f"{uploaded_file.name}: {exc}"
            )

        progress.progress(index / total)

    st.info(
        "Indexing may run in the background. "
        "Refresh the document list to check status."
    )


def render_document_panel():
    st.subheader("Your documents")

    uploaded_files = st.file_uploader(
        "Upload multiple PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key="pdf_upload",
    )

    if st.button("Upload selected files"):
        if not uploaded_files:
            st.warning("Select at least one PDF.")
        else:
            upload_documents(uploaded_files)

    if st.button("Refresh document list"):
        st.rerun()

    try:
        documents = load_documents()
    except Exception as exc:
        st.error(f"Could not load documents: {exc}")
        return []

    if not documents:
        st.info("Upload your first PDF to get started.")
        return []

    for document in documents:
        status = document.get("status", "unknown")
        st.write(
            f"**{document['filename']}** — {status}"
        )

        if status != "indexed":
            st.caption(
                "This document may not be searchable yet."
            )

    return documents


# --------------------------------------------------
# Chat and source citations
# --------------------------------------------------

def render_sources(sources):
    if not sources:
        st.caption("No source documents were returned.")
        return

    with st.expander("Sources used for this answer"):
        for index, source in enumerate(sources, start=1):
            filename = source.get(
                "filename", "Unknown document"
            )
            page = source.get("page")
            excerpt = source.get(
                "excerpt",
                source.get("content", ""),
            )

            page_label = (
                f", page {page}" if page is not None
                else ""
            )

            st.markdown(
                f"**{index}. {filename}{page_label}**"
            )

            if excerpt:
                st.write(excerpt)


def render_chat(documents):
    st.subheader("Ask your documents")

    indexed_documents = [
        document
        for document in documents
        if document.get("status") == "indexed"
    ]

    if not indexed_documents:
        st.info(
            "You need at least one indexed document "
            "before asking questions."
        )
        return

    choices = {
        "All accessible documents": None
    }

    for document in indexed_documents:
        label = (
            f"{document['filename']} "
            f"(ID: {document['id']})"
        )
        choices[label] = document["id"]

    selected_label = st.selectbox(
        "Search scope",
        list(choices.keys()),
        index=0,
        help=(
            "By default, search all indexed documents "
            "you are authorized to access."
        ),
    )

    selected_document_id = choices[selected_label]

    # Changing the scope starts a fresh conversation.
    current_scope = (
        str(selected_document_id)
        if selected_document_id is not None
        else "all"
    )

    if st.session_state.scope_key != current_scope:
        clear_chat()
        st.session_state.scope_key = current_scope

    if st.button("New conversation"):
        clear_chat()
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message.get("sources"):
                render_sources(message["sources"])

    question = st.chat_input(
        "Ask something about your documents..."
    )

    if not question:
        return

    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.markdown(question)

    payload = {"question": question}

    # Do not send document_id for all-document search.
    if selected_document_id is not None:
        payload["document_id"] = selected_document_id

    if st.session_state.conversation_id is not None:
        payload["conversation_id"] = (
            st.session_state.conversation_id
        )

    with st.chat_message("assistant"):
        with st.spinner("Searching your documents..."):
            try:
                result = api_request(
                    "POST",
                    "/rag/ask",
                    json=payload,
                )

                answer = result["answer"]
                sources = result.get("sources", [])

                st.markdown(answer)
                render_sources(sources)

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "sources": sources,
                    }
                )

                st.session_state.conversation_id = (
                    result.get("conversation_id")
                )

            except Exception as exc:
                st.error(str(exc))
                st.caption(
                    "Check that your backend supports "
                    "multi-document retrieval."
                )


# --------------------------------------------------
# Main application
# --------------------------------------------------

def main():
    if not API_BASE_URL:
        st.error(
            "Missing RAG_API_BASE_URL. "
            "Add it to your frontend .env file."
        )
        st.stop()

    if not st.session_state.access_token:
        authentication_screen()
        return

    with st.sidebar:
        st.title("RAG Assistant")

        if st.session_state.user:
            st.caption(
                f"Signed in as "
                f"{st.session_state.user.get('email', '')}"
            )

        if st.button("Logout"):
            st.session_state.access_token = None
            st.session_state.user = None
            clear_chat()
            st.rerun()

    st.title("📚 Multi-Document RAG Chat")

    try:
        documents = render_document_panel()
    except Exception as exc:
        st.error(str(exc))
        documents = []

    st.divider()
    render_chat(documents)


if __name__ == "__main__":
    main()