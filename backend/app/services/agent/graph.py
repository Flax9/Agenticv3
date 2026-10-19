"""
RKS Agentic RAG — Agent Graph
=============================================================
Three capabilities:
  1. direct_answer  — greetings / simple chat
  2. kb_answer      — RAG-based Q&A over RKS knowledge base
  3. document_maker — multi-turn RKS document generation pipeline
       upload_boq (interrupt, optional) → clarify_rks
       → retrieve_examples → generate_rks_json
       → review_rks (interrupt) → export_docx

State is persisted across turns via MemorySaver (checkpointer).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Annotated

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openrouter import ChatOpenRouter
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import interrupt
from pydantic import BaseModel, Field
from typing_extensions import TypedDict

from app.services.rag.vector_store import Vector_Store

load_dotenv()


# ──────────────────────────────────────────────────────────────
# State
# ──────────────────────────────────────────────────────────────

class RKSFields(TypedDict, total=False):
    """Metadata gathered from the user before generating the document."""
    judul_pekerjaan: str
    resiko_csms: str          # "HIGH" | "MIDDLE" | "LOW"
    nama_perusahaan: str
    nomor_dokumen: str
    tahun: str
    pengesahan: Dict[str, Any]


class AgentState(TypedDict):
    messages:       Annotated[List[BaseMessage], add_messages]
    kb_context:     List[Document]
    source_used:    str
    user_question:  str
    # Document-maker specific
    rks_fields:     Optional[RKSFields]       # clarification data collected so far
    rks_draft_json: Optional[Dict[str, Any]]  # structured draft ready for export
    boq_summary:    Optional[str]             # LLM-generated summary of the uploaded BoQ PDF



# ──────────────────────────────────────────────────────────────
# LLM instances
# ──────────────────────────────────────────────────────────────

llm = ChatOpenRouter(
    model="qwen/qwen3.7-flash",
    temperature=0,
)


# ──────────────────────────────────────────────────────────────
# Structured output schemas
# ──────────────────────────────────────────────────────────────

class RouteDecision(BaseModel):
    route: Literal["kb", "direct", "document_maker"] = Field(
        description=(
            "Use 'kb' for questions about RKS content or structure. "
            "Use 'document_maker' when the user wants to create/generate an RKS document. "
            "Use 'direct' only for greetings, thanks, or very simple chat."
        )
    )


class ExtractedFields(BaseModel):
    """Fields that can be parsed from the user's latest message."""
    judul_pekerjaan: Optional[str] = Field(None, description="Job/project title")
    resiko_csms: Optional[str]     = Field(None, description="CSMS risk: HIGH, MIDDLE, or LOW")
    nama_perusahaan: Optional[str] = Field(None, description="Company or unit name")
    nomor_dokumen: Optional[str]   = Field(None, description="Document number")
    tahun: Optional[str]           = Field(None, description="Year or date of the RKS")
    pengesahan: Optional[Dict[str, Any]] = Field(
        None,
        description=(
            "Approval info dict with keys: disusun_oleh, diperiksa_oleh, disetujui_oleh. "
            "Each value is a dict with 'nama' and 'jabatan'."
        ),
    )


router_llm     = llm.with_structured_output(RouteDecision,   method="json_schema")
extractor_llm  = llm.with_structured_output(ExtractedFields, method="json_schema")


# ──────────────────────────────────────────────────────────────
# Required RKS fields and helper
# ──────────────────────────────────────────────────────────────

REQUIRED_FIELDS = [
    "judul_pekerjaan",
    "resiko_csms",
    "nama_perusahaan",
    "nomor_dokumen",
    "tahun",
    "pengesahan",
]

FIELD_PROMPTS = {
    "judul_pekerjaan":  "Apa **judul pekerjaan** atau deskripsi singkat pekerjaan yang akan dibuat RKS-nya?",
    "resiko_csms":      "Berapa level **risiko CSMS** pekerjaan ini? (HIGH / MIDDLE / LOW)",
    "nama_perusahaan":  "Apa **nama perusahaan / unit** yang akan tercantum di dokumen?",
    "nomor_dokumen":    "Berapa **nomor dokumen** RKS ini?",
    "tahun":            "Berapa **tahun** atau tanggal penerbitan dokumen?",
    "pengesahan": (
        "Siapa yang **menyusun, memeriksa, dan menyetujui** dokumen ini? "
        "(Silakan sebutkan nama dan jabatan untuk masing-masing.)"
    ),
}


def _missing_fields(rks_fields: Optional[RKSFields]) -> List[str]:
    """Return list of required fields not yet collected."""
    if not rks_fields:
        return REQUIRED_FIELDS[:]
    return [f for f in REQUIRED_FIELDS if not rks_fields.get(f)]


def _merge_fields(existing: Optional[RKSFields], new: ExtractedFields) -> RKSFields:
    """Merge newly extracted fields into existing collected fields."""
    result: RKSFields = dict(existing) if existing else {}
    for field in REQUIRED_FIELDS:
        value = getattr(new, field, None)
        if value:  # Only merge truthy values (ignores None, "", {}, [])
            result[field] = value
    return result


# ──────────────────────────────────────────────────────────────
# Node 1 — Router
# ──────────────────────────────────────────────────────────────

def route_question(state: AgentState) -> Dict[str, Any]:
    """Classify the user's intent and update routing state."""
    last_msg = state["messages"][-1]
    question_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Short-circuit: if we're mid-clarification, skip upload_boq and go straight
    # to clarify_rks — avoids re-asking for the BoQ on every follow-up answer.
    if state.get("rks_fields") is not None and _missing_fields(state.get("rks_fields")):
        return {
            "source_used": "document_maker_clarify",
            "user_question": question_text,
        }

    decision = router_llm.invoke(
        f"""
You are a router for an Agentic RAG assistant about RKS (Rencana Kerja dan Syarat-Syarat) documents.

Route to "kb" if the user asks about:
- RKS content, structure, clauses, or requirements
- Questions that need knowledge from the RKS database

Route to "document_maker" if the user wants to:
- Create, generate, or make a new RKS document

Route to "direct" only for greetings, thanks, or very simple conversation.

User message: {question_text}

Return valid JSON. Example: {{"route": "kb"}}
"""
    )
    print(f"[Router] → {decision.route}")
    return {
        "source_used":   decision.route,
        "user_question": question_text,
    }


def route_after_router(state: AgentState) -> Literal["retrieve_kb", "direct_answer", "upload_boq", "clarify_rks"]:
    src = state["source_used"]
    if src == "kb":
        return "retrieve_kb"
    if src == "document_maker":
        return "upload_boq"           # fresh request → ask for BoQ first
    if src == "document_maker_clarify":
        return "clarify_rks"          # mid-session → skip straight to clarification
    return "direct_answer"


# ──────────────────────────────────────────────────────────────
# Node 2a — Direct answer
# ──────────────────────────────────────────────────────────────

def direct_answer(state: AgentState) -> Dict[str, Any]:
    """Answer simple / conversational messages."""
    response = llm.invoke(
        [SystemMessage(content="Kamu adalah asisten AI yang membantu. Jawab dengan ramah dan singkat.")]
        + state["messages"]
    )
    return {"messages": [response]}


# ──────────────────────────────────────────────────────────────
# Node 2b — KB retrieval path
# ──────────────────────────────────────────────────────────────

def retrieve_kb(state: AgentState) -> Dict[str, Any]:
    """Retrieve relevant RKS documents from the vector store."""
    query = state["user_question"]
    try:
        vs = Vector_Store()
        results = vs.doc_store.similarity_search(query, k=4)
        print(f"[Retrieve KB] Found {len(results)} docs")
        return {"kb_context": results}
    except Exception as e:
        print(f"[Retrieve KB] Error: {e}")
        return {"kb_context": []}


def kb_answer(state: AgentState) -> Dict[str, Any]:
    """Generate an answer grounded in the retrieved KB context."""
    context_text = "\n\n".join(
        f"[Doc {i+1}] {doc.page_content}"
        for i, doc in enumerate(state.get("kb_context", []))
    )
    system = SystemMessage(content=f"""
Kamu adalah asisten RKS (Rencana Kerja dan Syarat-Syarat) Pertamina.
Jawab pertanyaan pengguna berdasarkan konteks dokumen berikut.
Apabila konteks tidak mencukupi, sampaikan keterbatasan informasi dengan jujur.

Konteks:
{context_text}
""")
    response = llm.invoke([system] + state["messages"])
    return {"messages": [response]}


# ──────────────────────────────────────────────────────────────
# Node 3a — Upload Bill of Quantity (optional)
# ──────────────────────────────────────────────────────────────

_SKIP_KEYWORDS = {"skip", "lewati", "tidak", "no", "n", "tidak ada", "ga ada", "tidak punya"}

_boq_converter = None  # lazy-loaded Docling converter


def _get_docling_converter():
    """Lazily initialise the Docling DocumentConverter (heavy import)."""
    global _boq_converter
    if _boq_converter is None:
        from docling.document_converter import DocumentConverter
        _boq_converter = DocumentConverter()
    return _boq_converter


def _load_and_summarize_boq(file_path: str) -> str:
    """Load a PDF with Docling, export to markdown, then summarize with the LLM."""
    converter = _get_docling_converter()
    print(f"[BoQ] Loading PDF with Docling: {file_path}")
    result    = converter.convert(file_path)
    markdown  = result.document.export_to_markdown()
    print(f"[BoQ] Extracted {len(markdown)} chars of markdown. Summarizing...")

    system = SystemMessage(content=(
        "Kamu adalah asisten AI ahli yang bertugas mengekstrak informasi penting "
        "dari dokumen Bill of Quantity (BoQ) / Rencana Anggaran Biaya.\n\n"
        "Buatlah ringkasan terstruktur yang mencakup:\n"
        "1. Material utama yang digunakan\n"
        "2. Kuantitas atau volume pekerjaan\n"
        "3. Ruang lingkup spesifik proyek\n"
        "4. Persyaratan teknis khusus (jika ada)\n\n"
        "Ringkasan ini akan digunakan sebagai konteks tambahan untuk membuat dokumen RKS. "
        "Gunakan bahasa Indonesia yang baku dan jelas."
    ))
    human = HumanMessage(content=f"Dokumen BoQ:\n{markdown[:15000]}")
    response = llm.invoke([system, human])
    return response.content


def upload_boq(state: AgentState) -> Dict[str, Any]:
    """
    Ask the user to provide a BoQ PDF path (or skip).
    Uses interrupt() to pause the graph until the user responds.
    Validates the path, loads with Docling, and stores an LLM summary in state.
    """
    user_response: str = interrupt(
        "📎 Apakah Anda memiliki dokumen **Bill of Quantity (BoQ)** dalam format PDF?\n"
        "Jika ya, ketik **path lengkap** file PDF tersebut.\n"
        "Jika tidak, ketik **'skip'** untuk melanjutkan tanpa BoQ."
    )
    user_response = user_response.strip()

    # ── User chose to skip ──
    if user_response.lower() in _SKIP_KEYWORDS:
        return {
            "boq_summary": None,
            "messages": [AIMessage(content="✅ Melanjutkan tanpa BoQ. Mari mulai mengumpulkan informasi dokumen.")],
        }

    # ── Validate file path ──
    path = Path(user_response)
    if not path.exists():
        return {
            "messages": [AIMessage(
                content=f"❌ File tidak ditemukan: `{user_response}`\n"
                        "Pastikan path sudah benar, lalu coba lagi, atau ketik **'skip'** untuk melanjutkan."
            )],
        }
    if path.suffix.lower() != ".pdf":
        return {
            "messages": [AIMessage(
                content=f"❌ File bukan PDF: `{user_response}`\n"
                        "Harap berikan file dengan format `.pdf`, atau ketik **'skip'**."
            )],
        }

    # ── Load and summarize ──
    try:
        summary = _load_and_summarize_boq(str(path))
        return {
            "boq_summary": summary,
            "messages": [AIMessage(
                content=f"✅ **BoQ berhasil diproses!** Ringkasan telah disimpan sebagai konteks tambahan.\n\n"
                        f"**Ringkasan BoQ:**\n{summary}\n\n"
                        "Sekarang mari kumpulkan informasi dokumen RKS."
            )],
        }
    except Exception as e:
        return {
            "boq_summary": None,
            "messages": [AIMessage(
                content=f"⚠️ Gagal memproses BoQ: {e}\n"
                        "Melanjutkan tanpa BoQ."
            )],
        }


def route_after_boq(state: AgentState) -> Literal["upload_boq", "clarify_rks"]:
    """
    After upload_boq runs:
    - If the last AI message contains an error about file not found / not PDF
      (i.e. boq_summary was NOT updated and no skip either), loop back to re-ask.
    - Otherwise proceed to clarify_rks.
    """
    last_msg = state["messages"][-1]
    content  = last_msg.content if hasattr(last_msg, "content") else ""
    # Error messages start with ❌ — loop back so the user can retry
    if isinstance(content, str) and content.startswith("❌"):
        return "upload_boq"
    return "clarify_rks"


# ──────────────────────────────────────────────────────────────
# Node 3b — Clarify RKS fields
# ──────────────────────────────────────────────────────────────

def clarify_rks(state: AgentState) -> Dict[str, Any]:
    """
    Extract any newly provided field values from the last user message,
    merge them into rks_fields, then ask for the next missing field.
    When all fields are collected, signal completion via a special marker.
    """
    last_msg  = state["messages"][-1]
    user_text = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    # Find the last question asked by the AI for context
    last_ai_msg = ""
    if len(state["messages"]) >= 2:
        prev_msg = state["messages"][-2]
        if hasattr(prev_msg, "content") and prev_msg.__class__.__name__ in ("AIMessage", "ChatMessage"):
            last_ai_msg = prev_msg.content

    # Extract fields mentioned in the latest message
    extracted: ExtractedFields = extractor_llm.invoke(
        f"""
Extract any RKS document metadata from the user message below.
Return null for fields not mentioned.

The agent previously asked this question (use this context to understand short answers):
"{last_ai_msg}"

NOTE: For 'resiko_csms', if the user answers in Indonesian, map it:
- "tinggi" -> "HIGH"
- "sedang" -> "MIDDLE" 
- "rendah" -> "LOW"

User message: {user_text}

Return valid JSON matching the schema.
"""
    )
    print(f"[Debug] Extracted fields: {extracted}")

    rks_fields = _merge_fields(state.get("rks_fields"), extracted)
    missing    = _missing_fields(rks_fields)

    if not missing:
        # All fields collected — pass control to next node
        return {
            "rks_fields": rks_fields,
            "messages": [AIMessage(content="✅ Semua informasi telah terkumpul. Saya akan mencari referensi RKS serupa dan membuat draf dokumen...")],
        }

    # Still missing some fields — ask for the next one
    next_field = missing[0]
    question   = FIELD_PROMPTS[next_field]

    collected_summary = ""
    if rks_fields:
        lines = [f"  • **{k}**: {v}" for k, v in rks_fields.items() if v]
        if lines:
            collected_summary = "\n\nInformasi yang sudah terkumpul:\n" + "\n".join(lines)

    reply = AIMessage(content=f"{question}{collected_summary}")
    return {
        "rks_fields": rks_fields,
        "messages":   [reply],
    }


def route_after_clarify(state: AgentState) -> Literal["retrieve_examples", "__end__"]:
    """Continue to retrieval only once all fields are collected."""
    if not _missing_fields(state.get("rks_fields")):
        return "retrieve_examples"
    return "__end__"


# ──────────────────────────────────────────────────────────────
# Node 3b — Retrieve similar RKS examples
# ──────────────────────────────────────────────────────────────

def retrieve_examples(state: AgentState) -> Dict[str, Any]:
    """Search KB for RKS examples similar to the requested job type."""
    judul = (state.get("rks_fields") or {}).get("judul_pekerjaan", "RKS")
    query = f"Struktur dan isi RKS untuk pekerjaan {judul}"
    try:
        vs      = Vector_Store()
        results = vs.doc_store.similarity_search(query, k=5)
        print(f"[Retrieve Examples] Found {len(results)} docs for: {judul}")
        return {"kb_context": results}
    except Exception as e:
        print(f"[Retrieve Examples] Error: {e}")
        return {"kb_context": []}


# ──────────────────────────────────────────────────────────────
# Node 3c — Generate RKS JSON draft
# ──────────────────────────────────────────────────────────────

_RKS_JSON_SCHEMA = """
{
  "cover_page": {
    "judul_pekerjaan": "<string>",
    "resiko_csms": "<HIGH|MIDDLE|LOW>",
    "nama_perusahaan": "<string>"
  },
  "metadata": {
    "nomor_dokumen": "<string>",
    "tahun": "<string>"
  },
  "pengesahan": {
    "disusun_oleh":  {"nama": "<string>", "jabatan": "<string>"},
    "diperiksa_oleh":{"nama": "<string>", "jabatan": "<string>"},
    "disetujui_oleh":{"nama": "<string>", "jabatan": "<string>"}
  },
  "bab": [
    {
      "nomor": "I",
      "judul": "<string>",
      "sub_bab": [
        {
          "nomor": "1.1",
          "judul": "<string>",
          "tipe": "<paragraf|numbered_list|bullet_list|table|heading_only>",
          "konten": "<string or list or table dict>"
        }
      ]
    }
  ]
}
"""


def generate_rks_json(state: AgentState) -> Dict[str, Any]:
    """Generate a full structured RKS draft as JSON using the LLM."""
    fields = state.get("rks_fields") or {}
    context_text = "\n\n".join(
        f"[Referensi {i+1}]\n{doc.page_content}"
        for i, doc in enumerate(state.get("kb_context", []))
    )

    boq_section = ""
    if state.get("boq_summary"):
        boq_section = (
            f"\n\nBill of Quantity (BoQ) yang diberikan oleh user "
            f"(gunakan sebagai acuan ruang lingkup dan kuantitas pekerjaan):\n"
            f"{state['boq_summary']}\n"
        )

    system = SystemMessage(content=f"""
Kamu adalah generator dokumen RKS (Rencana Kerja dan Syarat-Syarat) Pertamina.

Buatlah dokumen RKS yang lengkap dan formal berdasarkan informasi berikut.
Gunakan referensi dokumen yang diberikan untuk menentukan struktur bab yang sesuai.

Informasi Dokumen:
- Judul Pekerjaan : {fields.get('judul_pekerjaan', '')}
- Risiko CSMS     : {fields.get('resiko_csms', 'HIGH')}
- Nama Perusahaan : {fields.get('nama_perusahaan', 'PT PERTAMINA (PERSERO)')}
- Nomor Dokumen   : {fields.get('nomor_dokumen', '')}
- Tahun           : {fields.get('tahun', '')}
- Pengesahan      : {json.dumps(fields.get('pengesahan', {}), ensure_ascii=False)}
{boq_section}
Referensi RKS Sejenis:
{context_text}

Output HARUS berupa JSON valid dengan schema berikut:
{_RKS_JSON_SCHEMA}

Buat minimal 5 bab (BAB I hingga BAB V atau lebih sesuai jenis pekerjaan).
Setiap bab harus memiliki konten yang relevan dan substantif.
Jawab HANYA dengan JSON, tanpa teks lain.
""")

    raw_response = llm.invoke([system])
    raw_text     = raw_response.content

    # Parse JSON from the LLM response
    try:
        # Strip markdown code fences if present
        clean = raw_text.strip()
        if clean.startswith("```"):
            clean = clean.split("```", 2)[1]
            if clean.startswith("json"):
                clean = clean[4:]
            clean = clean.rsplit("```", 1)[0]
        draft_json = json.loads(clean.strip())
    except json.JSONDecodeError as e:
        print(f"[Generate JSON] Parse error: {e}")
        draft_json = {"error": "JSON parse failed", "raw": raw_text}

    # Build a human-readable summary to show the user
    bab_list = draft_json.get("bab", [])
    bab_summary = "\n".join(
        f"  - BAB {b.get('nomor', '')} — {b.get('judul', '')}"
        for b in bab_list
    )
    summary_msg = AIMessage(content=f"""
📄 **Draf RKS telah dibuat!**

**Judul:** {fields.get('judul_pekerjaan', '')}
**Risiko CSMS:** {fields.get('resiko_csms', '')}
**Perusahaan:** {fields.get('nama_perusahaan', '')}
**No. Dokumen:** {fields.get('nomor_dokumen', '')}
**Tahun:** {fields.get('tahun', '')}

**Struktur Bab:**
{bab_summary}

---
Apakah Anda menyetujui draf ini untuk diekspor ke file `.docx`?
Ketik **"setuju"** untuk mengekspor, atau berikan instruksi perubahan jika ada yang perlu direvisi.
""")

    return {
        "rks_draft_json": draft_json,
        "messages":       [summary_msg],
    }


# ──────────────────────────────────────────────────────────────
# Node 3d — Human-in-the-loop review (interrupt)
# ──────────────────────────────────────────────────────────────

def review_rks(state: AgentState) -> Dict[str, Any]:
    """
    Pause execution and wait for explicit user approval via interrupt().
    The graph will resume with the user's response as the next HumanMessage.
    If approved → export. If revision requested → regenerate.
    """
    user_decision = interrupt(
        "Apakah Anda menyetujui draf RKS di atas? "
        "Ketik 'setuju' untuk ekspor atau berikan instruksi revisi."
    )
    return {"messages": [HumanMessage(content=str(user_decision))]}


def route_after_review(state: AgentState) -> Literal["export_docx", "generate_rks_json"]:
    """Route based on user's review decision."""
    last_msg = state["messages"][-1]
    content  = last_msg.content.lower().strip() if hasattr(last_msg, "content") else ""

    APPROVAL_KEYWORDS = {"setuju", "ok", "oke", "ya", "yes", "approve", "ekspor", "export", "lanjut"}
    if any(kw in content for kw in APPROVAL_KEYWORDS):
        return "export_docx"
    return "generate_rks_json"


# ──────────────────────────────────────────────────────────────
# Node 3e — Export to DOCX
# ──────────────────────────────────────────────────────────────

def export_docx(state: AgentState) -> Dict[str, Any]:
    """Call render_to_docx() and return the file path to the user."""
    from app.services.rag.docx_exporter import render_to_docx

    draft = state.get("rks_draft_json")
    if not draft or "error" in draft:
        return {
            "messages": [AIMessage(content="❌ Draf JSON tidak valid. Silakan coba generate ulang.")]
        }

    try:
        output_path = render_to_docx(draft)
        reply = AIMessage(content=f"✅ **Dokumen RKS berhasil dibuat!**\n\nFile tersimpan di:\n`{output_path}`")
    except Exception as e:
        reply = AIMessage(content=f"❌ Gagal membuat file DOCX: {e}")

    # Reset doc-maker state for next session
    return {
        "messages":       [reply],
        "rks_fields":     None,
        "rks_draft_json": None,
    }


# ──────────────────────────────────────────────────────────────
# Graph assembly
# ──────────────────────────────────────────────────────────────

def build_graph():
    builder = StateGraph(AgentState)

    # Register nodes
    builder.add_node("route_question",    route_question)
    builder.add_node("direct_answer",     direct_answer)
    builder.add_node("retrieve_kb",       retrieve_kb)
    builder.add_node("kb_answer",         kb_answer)
    builder.add_node("upload_boq",        upload_boq)        # NEW
    builder.add_node("clarify_rks",       clarify_rks)
    builder.add_node("retrieve_examples", retrieve_examples)
    builder.add_node("generate_rks_json", generate_rks_json)
    builder.add_node("review_rks",        review_rks)
    builder.add_node("export_docx",       export_docx)

    # Entry point
    builder.set_entry_point("route_question")

    # Router → dispatch
    builder.add_conditional_edges(
        "route_question",
        route_after_router,
        {
            "retrieve_kb":   "retrieve_kb",
            "direct_answer": "direct_answer",
            "upload_boq":    "upload_boq",    # fresh document_maker → BoQ upload first
            "clarify_rks":   "clarify_rks",   # mid-clarification short-circuit
        },
    )

    # KB path
    builder.add_edge("retrieve_kb", "kb_answer")
    builder.add_edge("kb_answer",   "__end__")

    # Direct path
    builder.add_edge("direct_answer", "__end__")

    # Document-maker path
    # upload_boq (interrupt) → route_after_boq → clarify_rks (or retry upload_boq on error)
    builder.add_conditional_edges(
        "upload_boq",
        route_after_boq,
        {
            "upload_boq":  "upload_boq",   # invalid path → retry
            "clarify_rks": "clarify_rks",
        },
    )
    builder.add_conditional_edges(
        "clarify_rks",
        route_after_clarify,
        {
            "retrieve_examples": "retrieve_examples",
            "__end__":           "__end__",
        },
    )
    builder.add_edge("retrieve_examples", "generate_rks_json")
    builder.add_edge("generate_rks_json", "review_rks")
    builder.add_conditional_edges(
        "review_rks",
        route_after_review,
        {
            "export_docx":       "export_docx",
            "generate_rks_json": "generate_rks_json",
        },
    )
    builder.add_edge("export_docx", "__end__")

    # Compile with MemorySaver so state persists across turns.
    # interrupt() calls INSIDE upload_boq and review_rks handle pausing —
    # no interrupt_before needed (that would cause a blank double-prompt).
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


graph = build_graph()
# png = graph.get_graph().draw_mermaid_png()

# with open('graph.png', 'wb') as p: 
#     p.write(png)
