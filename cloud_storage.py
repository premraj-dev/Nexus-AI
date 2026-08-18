"""Supabase authentication and cloud chat storage for Nexus AI."""

import datetime as dt
import os
import uuid
from typing import Any

from dotenv import load_dotenv
from supabase import Client, create_client


load_dotenv()


def is_configured() -> bool:
    return bool(os.getenv("SUPABASE_URL") and os.getenv("SUPABASE_ANON_KEY"))


def make_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_ANON_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_ANON_KEY are required.")
    return create_client(url, key)


def _data(response: Any) -> list[dict]:
    value = getattr(response, "data", None)
    return value if isinstance(value, list) else []


def session_tokens(session: Any) -> dict[str, str]:
    return {
        "access_token": session.access_token,
        "refresh_token": session.refresh_token,
    }


def sign_up(client: Client, email: str, password: str) -> tuple[Any, str | None]:
    response = client.auth.sign_up({"email": email, "password": password})
    session = getattr(response, "session", None)
    message = None if session else "Check your email to confirm the account, then sign in."
    return session, message


def sign_in(client: Client, email: str, password: str) -> Any:
    response = client.auth.sign_in_with_password({"email": email, "password": password})
    return response.session


class GuestChatStore:
    """Session-only chat storage. It never writes guest data to Supabase."""

    def __init__(self, state: dict):
        state.setdefault("guest_chats", {})
        state.setdefault("guest_messages", {})
        self.state = state

    def list_chats(self, search: str = "") -> list[dict]:
        chats = list(self.state["guest_chats"].values())
        chats.sort(key=lambda item: item["updated_at"], reverse=True)
        chats.sort(key=lambda item: item.get("is_pinned", False), reverse=True)
        if not search.strip():
            return chats
        needle = search.strip().lower()
        return [
            chat for chat in chats
            if needle in chat["title"].lower()
            or any(needle in msg["content"].lower() for msg in self.state["guest_messages"].get(chat["id"], []))
        ]

    def create_chat(self, title: str = "New chat") -> dict:
        chat_id = str(uuid.uuid4())
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        chat = {
            "id": chat_id,
            "title": title[:80] or "New chat",
            "is_pinned": False,
            "created_at": now,
            "updated_at": now,
        }
        self.state["guest_chats"][chat_id] = chat
        self.state["guest_messages"][chat_id] = []
        return chat

    def get_chat(self, chat_id: str) -> dict | None:
        return self.state["guest_chats"].get(chat_id)

    def rename_chat(self, chat_id: str, title: str) -> None:
        chat = self.get_chat(chat_id)
        if chat:
            chat["title"] = title[:80] or "New chat"
            chat["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    def set_pinned(self, chat_id: str, is_pinned: bool) -> None:
        chat = self.get_chat(chat_id)
        if chat:
            chat["is_pinned"] = is_pinned
            chat["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    def delete_chat(self, chat_id: str) -> None:
        self.state["guest_chats"].pop(chat_id, None)
        self.state["guest_messages"].pop(chat_id, None)

    def get_messages(self, chat_id: str) -> list[dict]:
        return list(self.state["guest_messages"].get(chat_id, []))

    def add_message(self, chat_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        if chat_id not in self.state["guest_messages"]:
            self.state["guest_messages"][chat_id] = []
        self.state["guest_messages"][chat_id].append({
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        })
        chat = self.get_chat(chat_id)
        if chat:
            chat["updated_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    def migrate_to_cloud(self, cloud_store: "CloudChatStore") -> str | None:
        """Copy guest chats into the authenticated account and return the active chat id."""
        active_id = None
        for chat in self.list_chats():
            cloud_chat = cloud_store.create_chat(chat["title"])
            cloud_store.set_pinned(cloud_chat["id"], chat.get("is_pinned", False))
            for message in self.get_messages(chat["id"]):
                cloud_store.add_message(cloud_chat["id"], message["role"], message["content"])
            active_id = cloud_chat["id"]
        return active_id


class CloudChatStore:
    def __init__(self, client: Client, user_id: str):
        self.client = client
        self.user_id = user_id

    def list_chats(self, search: str = "") -> list[dict]:
        response = (
            self.client.table("chats")
            .select("id,title,is_pinned,created_at,updated_at")
            .eq("user_id", self.user_id)
            .order("is_pinned", desc=True)
            .order("updated_at", desc=True)
            .limit(100)
            .execute()
        )
        chats = _data(response)
        if not search.strip():
            return chats

        needle = search.strip().lower()
        title_matches = {chat["id"] for chat in chats if needle in chat.get("title", "").lower()}
        message_response = (
            self.client.table("messages")
            .select("chat_id")
            .eq("user_id", self.user_id)
            .ilike("content", f"%{search.strip()}%")
            .limit(500)
            .execute()
        )
        message_matches = {row["chat_id"] for row in _data(message_response)}
        return [chat for chat in chats if chat["id"] in title_matches or chat["id"] in message_matches]

    def create_chat(self, title: str = "New chat") -> dict:
        response = (
            self.client.table("chats")
            .insert({"user_id": self.user_id, "title": title[:80] or "New chat"})
            .select()
            .single()
            .execute()
        )
        return response.data

    def get_chat(self, chat_id: str) -> dict | None:
        response = (
            self.client.table("chats")
            .select("id,title,is_pinned,created_at,updated_at")
            .eq("id", chat_id)
            .eq("user_id", self.user_id)
            .maybe_single()
            .execute()
        )
        return response.data

    def rename_chat(self, chat_id: str, title: str) -> None:
        (
            self.client.table("chats")
            .update({"title": title[:80] or "New chat"})
            .eq("id", chat_id)
            .eq("user_id", self.user_id)
            .execute()
        )

    def set_pinned(self, chat_id: str, is_pinned: bool) -> None:
        (
            self.client.table("chats")
            .update({"is_pinned": is_pinned})
            .eq("id", chat_id)
            .eq("user_id", self.user_id)
            .execute()
        )

    def delete_chat(self, chat_id: str) -> None:
        (
            self.client.table("chats")
            .delete()
            .eq("id", chat_id)
            .eq("user_id", self.user_id)
            .execute()
        )

    def get_messages(self, chat_id: str) -> list[dict]:
        response = (
            self.client.table("messages")
            .select("id,role,content,created_at")
            .eq("chat_id", chat_id)
            .eq("user_id", self.user_id)
            .order("created_at", desc=False)
            .order("id", desc=False)
            .limit(1000)
            .execute()
        )
        return _data(response)

    def add_message(self, chat_id: str, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("role must be user or assistant")
        (
            self.client.table("messages")
            .insert(
                {
                    "chat_id": chat_id,
                    "user_id": self.user_id,
                    "role": role,
                    "content": content,
                }
            )
            .execute()
        )
        (
            self.client.table("chats")
            .update({"updated_at": dt.datetime.now(dt.timezone.utc).isoformat()})
            .eq("id", chat_id)
            .eq("user_id", self.user_id)
            .execute()
        )
