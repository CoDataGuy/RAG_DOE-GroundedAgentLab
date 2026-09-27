# =============================================================================
# rag_helpers.py
# -----------------------------------------------------------------------------
# Purpose:  Shared RAG setup functions for Clue rules agent notebooks.
#           Centralises chunking, embedding, reranking, contextualisation,
#           and retriever construction so multiple notebooks can import and
#           reuse them without duplicating code.
#
# Usage:
#   from rag_helpers import build_clue_retriever, tools
#
#   retriever, search_clue_instructions = build_clue_retriever(
#       embedding_client,
#       "../References/ClueRules.md"
#   )
#
# Design notes:
#   build_clue_retriever() uses a factory pattern:
#     - generate_embedding  closes over embedding_client (injected by caller)
#     - search_clue_instructions closes over the built retriever
#   Both are returned so the notebook has access to them without needing to
#   know anything about their internal dependencies.
# =============================================================================

import re
import json

import llm_helpers
from llm_helpers import chat, add_user_message, add_assistant_message, text_from_message
from retriever_implementation import VectorIndex, BM25Index, Retriever


# -----------------------------------------------------------------------------
# 1. CHUNKING
# -----------------------------------------------------------------------------

def chunk_by_section(document_text):
    """Split document into sections by ## headers."""
    return re.split(r"\n## ", document_text)


# -----------------------------------------------------------------------------
# 2. RERANKER
#    Uses Claude (via llm_helpers) to pick the k most relevant chunks.
#    llm_helpers must be initialised before this is called.
# -----------------------------------------------------------------------------

def reranker_fn(docs, query_text, k):
    """Use Claude to rerank retrieved documents."""
    joined_docs = "\n".join([
        f"""
        <document>
        <document_id>{doc["id"]}</document_id>
        <document_content>{doc["content"]}</document_content>
        </document>
        """
        for doc in docs
    ])

    prompt = f"""
    You are about to be given a set of documents, along with an id of each.
    Your task is to select the {k} most relevant documents to answer the user's question.

    Here is the user's question:
    <question>
    {query_text}
    </question>

    Here are the documents to select from:
    <documents>
    {joined_docs}
    </documents>

    Respond in the following format:
    ```json
    {{
        "document_ids": str[]
    }}
    ```
    """

    messages = []
    add_user_message(messages, prompt)
    add_assistant_message(messages, "```json")

    result = chat(messages, stop_sequences=["```"])
    return json.loads(text_from_message(result))["document_ids"]


# -----------------------------------------------------------------------------
# 3. CONTEXTUAL CHUNK ENHANCEMENT
#    Adds a short situating sentence before each chunk to improve retrieval.
#    Uses Claude (via llm_helpers) — llm_helpers must be initialised first.
# -----------------------------------------------------------------------------

def add_context(text_chunk, source_text):
    """Prepend a short situating context snippet to a chunk."""
    prompt = f"""
    Write a short and succinct snippet of text to situate this chunk within the
    overall source document for the purposes of improving search retrieval of the chunk.

    Here is the original source document:
    <document>
    {source_text}
    </document>

    Here is the chunk we want to situate within the whole document:
    <chunk>
    {text_chunk}
    </chunk>

    Answer only with the succinct context and nothing else.
    """

    messages = []
    add_user_message(messages, prompt)
    result = chat(messages)
    return text_from_message(result) + "\n" + text_chunk


# -----------------------------------------------------------------------------
# 4. TOOL SCHEMA
#    Pure data — the JSON schema Claude uses to call search_clue_instructions.
#    Defined here so every notebook imports the same definition.
# -----------------------------------------------------------------------------

tools = [
    {
        "name": "search_clue_instructions",
        "description": (
            "Search the official Clue game instructions to find information about "
            "rules, gameplay, setup, winning conditions, and player counts. "
            "Use this tool whenever you need specific information from the Clue game manual."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "The search query - what information to look for in the Clue "
                        "instructions (e.g., 'player count', 'how to win', 'setup rules')"
                    )
                }
            },
            "required": ["query"]
        }
    }
]


# -----------------------------------------------------------------------------
# 5. RETRIEVER FACTORY
#    Loads the document, builds the hybrid retriever with contextualised chunks,
#    and returns both the retriever and a ready-to-use search function.
#
#    Why a factory?
#    generate_embedding needs embedding_client (a VoyageAI client created in
#    the notebook from the API key).  We accept it here and close over it so
#    that the returned search function is self-contained — callers never need
#    to pass a client on every search call.
# -----------------------------------------------------------------------------

def build_clue_retriever(embedding_client, doc_path,
                         num_start_chunks=2, num_prev_chunks=2):
    """
    Build a hybrid BM25 + vector retriever for the Clue rules document.

    Args:
        embedding_client:    Initialised VoyageAI client.
        doc_path (str):      Path to ClueRules.md.
        num_start_chunks (int): Leading chunks added as context window.
        num_prev_chunks  (int): Preceding chunks added as context window.

    Returns:
        tuple: (retriever, search_clue_instructions)
            retriever                 — the Retriever object (for inspection/reuse)
            search_clue_instructions  — callable(query, k=3) -> JSON string
    """

    # ── Embedding function (closed over embedding_client) ────────────────────
    def generate_embedding(chunks, model="voyage-3-large", input_type="query"):
        is_list = isinstance(chunks, list)
        input_data = chunks if is_list else [chunks]
        result = embedding_client.embed(input_data, model=model, input_type=input_type)
        return result.embeddings if is_list else result.embeddings[0]

    # ── Load document ─────────────────────────────────────────────────────────
    with open(doc_path, "r") as f:
        clue_instructions = f.read()

    chunks = chunk_by_section(clue_instructions)
    print(f"  Loaded {len(chunks)} chunks from {doc_path}")

    # ── Build retriever ───────────────────────────────────────────────────────
    vector_index = VectorIndex(embedding_fn=generate_embedding)
    bm25_index   = BM25Index()
    retriever    = Retriever(bm25_index, vector_index, reranker_fn=reranker_fn)

    # ── Contextualise and index chunks ────────────────────────────────────────
    contextualized_chunks = []
    print(f"  Contextualising {len(chunks)} chunks...")

    for i, chunk in enumerate(chunks):
        context_parts = list(chunks[:min(num_start_chunks, len(chunks))])
        context_parts += chunks[max(0, i - num_prev_chunks):i]
        context = "\n".join(context_parts)
        contextualized_chunks.append(add_context(chunk, context))
        print(f"    chunk {i + 1}/{len(chunks)}")

    retriever.add_documents([
        {"content": chunk, "chunk_number": i + 1}
        for i, chunk in enumerate(contextualized_chunks)
    ])

    print(f"  Retriever ready — {len(contextualized_chunks)} chunks indexed")

    # ── Search function (closed over retriever) ───────────────────────────────
    def search_clue_instructions(query, k=3):
        """Search Clue rules; returns a JSON string with chunk results."""
        results = retriever.search(query, k=k)
        formatted = []
        for doc, score in results:
            content = doc["content"]
            preview = content[:200].strip()
            if len(content) > 200:
                preview += "..."
            formatted.append({
                "chunk_id":        f"CHUNK_{doc['chunk_number']}",
                "content":         content,
                "preview":         preview,
                "relevance_score": float(score)
            })
        return json.dumps(formatted, indent=2)

    return retriever, search_clue_instructions
