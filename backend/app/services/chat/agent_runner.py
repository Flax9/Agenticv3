"""Penghubung chat web ↔ agent LangGraph milik tim AI (`app.services.agent.graph`).

Modul milik tim web: hanya menjalankan graph seperti `main.py` di camp (invoke biasa,
atau `Command(resume=...)` saat graph berhenti di `interrupt()`), lalu merangkum hasil
satu giliran percakapan. Logika agent tidak diubah.

Satu sesi chat = satu `thread_id` LangGraph. Checkpointer agent masih MemorySaver
(di memori proses), jadi progres agent hilang saat server restart; riwayat chat tetap
tersimpan di database.
"""

import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

# Node yang memakai interrupt(): balasan user berikutnya harus dikirim sebagai resume
INTERRUPT_NODES = {"upload_boq", "review_rks"}
# Pesan export_docx berisi path berkas di dalam backtick
_DOCX_PATH = re.compile(r"`([^`\n]+\.docx)`")
# Node yang token jawabannya aman diteruskan ke user. Node lain memakai structured output
# (token JSON) atau menghasilkan draf JSON, jadi hanya dilaporkan sebagai progres.
STREAM_NODES = {"direct_answer", "kb_answer"}

EventCallback = Callable[[str, dict], None]


@dataclass
class AgentTurn:
    replies: list[str]
    awaiting: str | None  # node interrupt yang menunggu jawaban user
    fields: dict | None  # rks_fields yang sudah terkumpul
    new_draft: dict | None  # rks_draft_json bila giliran ini menghasilkan draf baru/revisi
    docx_path: Path | None  # berkas .docx bila giliran ini mengekspor dokumen


class RksAgentRunner:
    def __init__(self, graph=None):
        self._graph = graph
        self._init_lock = threading.Lock()

    @property
    def graph(self):
        # Import ditunda: modul agent membuat klien LLM saat diimpor
        if self._graph is None:
            with self._init_lock:
                if self._graph is None:
                    from app.services.agent.graph import graph

                    self._graph = graph
        return self._graph

    def is_skip_answer(self, text: str) -> bool:
        """Apakah teks dianggap 'lewati' oleh node upload_boq (kata kunci milik agent)."""
        from app.services.agent.graph import _SKIP_KEYWORDS

        return text.strip().lower() in _SKIP_KEYWORDS

    def awaiting(self, thread_id: str) -> str | None:
        snapshot = self.graph.get_state(_config(thread_id))
        return _paused_node(snapshot)

    def run_turn(self, thread_id: str, text: str, on_event: EventCallback | None = None) -> AgentTurn:
        """Jalankan satu giliran (sinkron; panggil lewat threadpool).

        Bila `on_event` diberikan, graph dijalankan dengan `stream()` dan melaporkan
        `("progress", {"node": ...})` saat node mulai, serta `("token", {"text": ...})`
        untuk token jawaban dari node di STREAM_NODES.
        """
        from langchain_core.messages import AIMessage, HumanMessage
        from langgraph.types import Command

        graph, config = self.graph, _config(thread_id)
        before = graph.get_state(config)
        values_before = before.values or {}
        n_before = len(values_before.get("messages", []))

        payload = Command(resume=text) if _paused_node(before) else {"messages": [HumanMessage(content=text)]}
        if on_event is None:
            graph.invoke(payload, config=config)
        else:
            for mode, event in graph.stream(payload, config=config, stream_mode=["tasks", "messages"]):
                if mode == "tasks" and "input" in event:
                    on_event("progress", {"node": event["name"]})
                elif mode == "messages":
                    chunk, metadata = event
                    content = getattr(chunk, "content", None)
                    if metadata.get("langgraph_node") in STREAM_NODES and isinstance(content, str) and content:
                        on_event("token", {"text": content})

        after = graph.get_state(config)
        values = after.values or {}
        replies = [
            m.content
            for m in values.get("messages", [])[n_before:]
            if isinstance(m, AIMessage) and isinstance(m.content, str) and m.content.strip()
        ]
        awaiting = _paused_node(after)
        if awaiting and after.interrupts:
            replies.append(str(after.interrupts[0].value))

        draft = values.get("rks_draft_json")
        is_new = isinstance(draft, dict) and "error" not in draft and draft != values_before.get("rks_draft_json")
        docx_path = next(
            (Path(m.group(1)) for r in replies if (m := _DOCX_PATH.search(r)) and Path(m.group(1)).is_file()),
            None,
        )
        return AgentTurn(
            replies=replies,
            awaiting=awaiting,
            fields=values.get("rks_fields"),
            new_draft=draft if is_new else None,
            docx_path=docx_path,
        )


def _config(thread_id: str) -> dict:
    return {"configurable": {"thread_id": thread_id}}


def _paused_node(snapshot) -> str | None:
    paused = set(snapshot.next or ()) & INTERRUPT_NODES
    return next(iter(paused)) if paused else None


rks_runner = RksAgentRunner()
