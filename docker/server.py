#!/usr/bin/env python3
"""NLS Inference Server - Local deployment without Modal.

This server provides both the pipeline and vLLM-compatible endpoints
that nectar expects. Run with Docker or directly with Python.

Architecture: Hybrid NER + NLS
    When both pipeline and model are available, runs NER and NLS in parallel,
    then merges results (NLS primary, NER augments missing fields).
    Set HYBRID_MODE=false to disable and use NER-only when pipeline available.

Endpoints:
    POST /v1/chat/completions - OpenAI-compatible chat endpoint (vLLM style)
    POST /pipeline - Hybrid NER+NLS pipeline endpoint
    GET /health - Health check
    GET /v1/models - List available models
    GET /debug/pipeline - Debug NER pipeline only
    GET /debug/hybrid - Debug hybrid merge details

Usage:
    # With Docker (GPU):
    docker run --gpus all -p 8000:8000 nls-server

    # With Docker (CPU):
    docker run -p 8000:8000 -e DEVICE=cpu nls-server

    # Direct Python:
    MODEL_NAME=adsabs/NLQT-Qwen3-1.7B python docker/server.py
"""

import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

# Configuration
MODEL_NAME = os.environ.get("MODEL_NAME", "adsabs/NLQT-Qwen3-1.7B")
DEVICE = os.environ.get("DEVICE", "cuda" if torch.cuda.is_available() else "cpu")
PORT = int(os.environ.get("PORT", 8000))
HYBRID_MODE = os.environ.get("HYBRID_MODE", "true").lower() in ("true", "1", "yes")
RAG_ENABLED = os.environ.get("RAG_ENABLED", "true").lower() in ("true", "1", "yes")
RAG_NUM_EXAMPLES = int(os.environ.get("RAG_NUM_EXAMPLES", "3"))
RAG_MAX_CARDS = int(os.environ.get("RAG_MAX_CARDS", "2"))
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "1.5"))
SYSTEM_PROMPT = '''Convert natural language to ADS/SciX search query. Output JSON: {"query": "..."}

Example:
User: Query: papers by Hawking on black holes from the 1970s
Date: 2025-03-16
Assistant: {"query": "author:\\"Hawking, S\\" abs:\\"black holes\\" pubdate:[1970 TO 1979]"}'''

# Try to import pipeline components (optional, for full pipeline mode)
try:
    # Docker: /app has finetune. Local: use project root for packages/finetune/src
    _project_root = Path(__file__).resolve().parent.parent
    for path in ["/app", str(_project_root / "packages" / "finetune" / "src")]:
        if path not in sys.path:
            sys.path.insert(0, path)
    from finetune.domains.scix.pipeline import process_query, is_ads_query
    from finetune.domains.scix.validate import lint_query, validate_field_constraints
    from finetune.domains.scix.institution_lookup import rewrite_aff_to_inst_or_aff
    from finetune.domains.scix.bibstem_lookup import rewrite_bibstem_values
    from finetune.domains.scix.assembler import rewrite_complex_author_wildcards
    from finetune.domains.scix.uat_lookup import rewrite_abs_to_abs_or_uat
    from finetune.domains.scix.planetary_feature_lookup import rewrite_abs_to_abs_or_planetary_feature
    from finetune.domains.scix.merge import merge_ner_and_nls, merge_ner_and_nls_intent, MergeResult
    from finetune.domains.scix.intent_spec import IntentSpec
    from finetune.domains.scix.rag_retrieval import retrieve_few_shot, reset_intent_cache
    from finetune.domains.scix.field_cards import select_cards
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_AVAILABLE = False
    print(f"Pipeline not available: {e}")
    rewrite_aff_to_inst_or_aff = None  # type: ignore[assignment]
    rewrite_bibstem_values = None  # type: ignore[assignment]
    rewrite_complex_author_wildcards = None  # type: ignore[assignment]
    rewrite_abs_to_abs_or_uat = None  # type: ignore[assignment]
    rewrite_abs_to_abs_or_planetary_feature = None  # type: ignore[assignment]
    merge_ner_and_nls = None  # type: ignore[assignment]
    merge_ner_and_nls_intent = None  # type: ignore[assignment]
    is_ads_query = None  # type: ignore[assignment]
    IntentSpec = None  # type: ignore[assignment, misc]
    retrieve_few_shot = None  # type: ignore[assignment]
    select_cards = None  # type: ignore[assignment]
    print("Pipeline modules not available - using model-only mode")

# ---------------------------------------------------------------------------
# Telemetry logger — structured JSON for query analytics
# ---------------------------------------------------------------------------
_telemetry_logger = logging.getLogger("nls.telemetry")
_telemetry_handler = logging.StreamHandler()
_telemetry_handler.setFormatter(logging.Formatter("%(message)s"))
_telemetry_logger.addHandler(_telemetry_handler)
_telemetry_logger.setLevel(logging.INFO)
_telemetry_logger.propagate = False  # Don't duplicate to root logger


def _log_telemetry(
    nl_query: str,
    final_query: str,
    source: str,
    confidence: float = 0.0,
    fields_injected: list[str] | None = None,
    rag_enabled: bool = False,
    rag_few_shot_count: int = 0,
    rag_cards_used: list[str] | None = None,
    latency_ms: float = 0.0,
    ner_ms: float = 0.0,
    llm_ms: float = 0.0,
    merge_ms: float = 0.0,
    error: str | None = None,
    repairs_applied: list[str] | None = None,
):
    """Log structured telemetry for a query."""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "nl_query": nl_query[:500],  # Truncate for safety
        "final_query": final_query[:1000],
        "source": source,
        "confidence": round(confidence, 3),
        "fields_injected": fields_injected or [],
        "rag_enabled": rag_enabled,
        "rag_few_shot_count": rag_few_shot_count,
        "rag_cards_used": rag_cards_used or [],
        "latency_ms": round(latency_ms, 1),
        "ner_ms": round(ner_ms, 1),
        "llm_ms": round(llm_ms, 1),
        "merge_ms": round(merge_ms, 1),
        "error": error,
        "repairs_applied": repairs_applied or [],
    }
    _telemetry_logger.info(json.dumps(entry))


app = FastAPI(
    title="NLS Inference Server",
    description="Natural Language to ADS Query translation",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model and tokenizer
model = None
tokenizer = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    model: str = "llm"
    messages: list[ChatMessage]
    max_tokens: int = 256
    temperature: float = 0.0
    chat_template_kwargs: dict = {}


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: list[ChatChoice]
    usage: ChatUsage


class PipelineRequest(BaseModel):
    model: str = "pipeline"
    messages: list[ChatMessage]


class PipelineDebugInfo(BaseModel):
    ner_time_ms: float = 0
    retrieval_time_ms: float = 0
    assembly_time_ms: float = 0
    nls_time_ms: float = 0
    merge_time_ms: float = 0
    total_time_ms: float = 0
    constraint_corrections: list[str] = []
    fallback_reason: str | None = None
    raw_extracted: dict | None = None
    merge_source: str | None = None  # "hybrid", "nls_only", "ner_only"
    fields_injected: list[str] = []
    nls_query: str | None = None
    ner_query: str | None = None


class PipelineResult(BaseModel):
    query: str
    intent: dict = {}
    retrieved_examples: list[dict] = []
    debug_info: PipelineDebugInfo
    success: bool = True
    error: str | None = None


class PipelineResponse(BaseModel):
    choices: list[ChatChoice]
    pipeline_result: PipelineResult | None = None
    error: str | None = None
    fallback: bool = False


def _find_checkpoint_dir(repo_id: str) -> str | None:
    """Find the latest checkpoint subdirectory in a HF repo (for LoRA adapters)."""
    try:
        from huggingface_hub import list_repo_files
        files = list_repo_files(repo_id)
        # Look for checkpoint dirs with adapter_config.json
        checkpoints = sorted(
            {f.split("/")[0] for f in files if "/" in f and f.endswith("adapter_config.json")},
            key=lambda x: int(x.split("-")[-1]) if x.split("-")[-1].isdigit() else 0,
        )
        return checkpoints[-1] if checkpoints else None
    except Exception:
        return None


def load_model():
    """Load the fine-tuned model (supports both full models and LoRA adapters)."""
    global model, tokenizer

    print(f"Loading model: {MODEL_NAME}")
    print(f"Device: {DEVICE}")

    dtype = torch.float16 if DEVICE != "cpu" else torch.float32

    # Check if this is a LoRA adapter repo (has checkpoint subdirs)
    checkpoint = _find_checkpoint_dir(MODEL_NAME)

    if checkpoint:
        print(f"Detected LoRA adapter (checkpoint: {checkpoint})")
        adapter_path = f"{MODEL_NAME}/{checkpoint}" if "/" not in checkpoint else checkpoint

        # Load adapter config to find base model
        from huggingface_hub import hf_hub_download
        adapter_config_path = hf_hub_download(MODEL_NAME, f"{checkpoint}/adapter_config.json")
        with open(adapter_config_path) as f:
            adapter_config = json.load(f)
        base_model_name = adapter_config["base_model_name_or_path"]

        # If base model is a quantized variant (bnb-4bit), use the full-precision version
        # bitsandbytes quantization is CUDA-only and won't work on MPS/CPU
        if "bnb-4bit" in base_model_name or "bnb-8bit" in base_model_name:
            # Map unsloth quantized models to their full-precision equivalents
            # e.g. "unsloth/qwen3-1.7b-unsloth-bnb-4bit" -> "Qwen/Qwen3-1.7B"
            model_class = adapter_config.get("auto_mapping", {}).get("base_model_class", "")
            if "Qwen3" in model_class:
                # Extract size from the name
                import re
                size_match = re.search(r'(\d+\.?\d*[bBmM])', base_model_name)
                size = size_match.group(1).upper() if size_match else "1.7B"
                base_model_name = f"Qwen/Qwen3-{size}"
            print(f"Quantized base model detected, using full-precision: {base_model_name}")
        print(f"Base model: {base_model_name}")

        # Load tokenizer from checkpoint
        tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME, subfolder=checkpoint, trust_remote_code=True
        )

        # Load base model
        from peft import PeftModel
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=dtype,
            device_map=DEVICE if DEVICE != "cpu" else None,
            trust_remote_code=True,
        )

        # Apply LoRA adapter
        model = PeftModel.from_pretrained(
            base_model, MODEL_NAME, subfolder=checkpoint, torch_dtype=dtype
        )
        model = model.merge_and_unload()
        print("LoRA adapter merged successfully")
    else:
        # Standard full model loading
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_NAME,
            torch_dtype=dtype,
            device_map=DEVICE if DEVICE != "cpu" else None,
            trust_remote_code=True,
        )

    if DEVICE == "cpu":
        model = model.to("cpu")

    print(f"Model loaded successfully on {DEVICE}")


def generate_query(messages: list[ChatMessage], max_tokens: int = 256, raw: bool = False) -> tuple[str, int, int]:
    """Generate ADS query from chat messages.

    Args:
        messages: Chat messages including system prompt.
        max_tokens: Maximum tokens to generate.
        raw: If True, return raw decoded text without post-processing.
             Used by hybrid path which handles parsing separately.

    Returns:
        Tuple of (generated_text, prompt_tokens, completion_tokens)
    """
    # Ensure system prompt is present
    message_dicts = [{"role": m.role, "content": m.content} for m in messages]
    if not any(m["role"] == "system" for m in message_dicts):
        message_dicts.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
    prompt = tokenizer.apply_chat_template(
        message_dicts,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(prompt, return_tensors="pt")
    if DEVICE != "cpu":
        inputs = inputs.to(model.device)

    prompt_tokens = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    # Decode only the generated part
    generated_ids = outputs[0][prompt_tokens:]
    completion_tokens = len(generated_ids)

    response = tokenizer.decode(generated_ids, skip_special_tokens=True).strip()

    # Raw mode: return unprocessed text for hybrid path
    if raw:
        return response, prompt_tokens, completion_tokens

    # Handle thinking mode output
    if "<think>" in response:
        parts = response.split("</think>")
        if len(parts) > 1:
            response = parts[-1].strip()

    # Try to extract JSON query
    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            json_str = response[json_start:json_end]
            data = json.loads(json_str)
            response = data.get("query", response)
    except json.JSONDecodeError:
        pass

    # Post-process: rewrite aff: to (inst: OR aff:) for known institutions
    if rewrite_aff_to_inst_or_aff is not None:
        response = rewrite_aff_to_inst_or_aff(response)

    # Post-process: fix bibstem values (full names -> abbreviations, add quotes)
    if rewrite_bibstem_values is not None:
        response = rewrite_bibstem_values(response)

    # Post-process: wildcard complex author names (hyphens, apostrophes)
    if rewrite_complex_author_wildcards is not None:
        response = rewrite_complex_author_wildcards(response)

    # Post-process: augment abs: with matching UAT terms for better recall
    if rewrite_abs_to_abs_or_uat is not None:
        response = rewrite_abs_to_abs_or_uat(response)

    # Post-process: augment abs: with matching planetary feature terms
    if rewrite_abs_to_abs_or_planetary_feature is not None:
        response = rewrite_abs_to_abs_or_planetary_feature(response)

    return response, prompt_tokens, completion_tokens


def build_rag_messages(
    messages: list[ChatMessage],
    few_shot: list[dict],
    cards: list[str] | None = None,
) -> list[ChatMessage]:
    """Insert few-shot examples and field cards into message list before the user query.

    Args:
        messages: Original messages [system, user, ...].
        few_shot: List of {"nl": str, "intent_json": dict, "think_trace": str}.
        cards: Optional list of field reference card strings.

    Returns:
        Augmented message list with few-shot examples before the user query.
    """
    if not few_shot and not cards:
        return messages

    result = []

    # System prompt — optionally append field reference cards
    if messages and messages[0].role == "system":
        system_content = messages[0].content
        if cards:
            cards_block = "\n\nReference:\n" + "\n".join(f"- {c}" for c in cards)
            system_content += cards_block
        result.append(ChatMessage(role="system", content=system_content))
        remaining = messages[1:]
    else:
        remaining = list(messages)

    # Insert few-shot examples as user/assistant pairs
    for ex in few_shot:
        result.append(ChatMessage(
            role="user",
            content=f"Query: {ex['nl']}\nDate: 2025-12-15",
        ))
        think_block = f"<think>\n{ex['think_trace']}\n</think>\n" if ex.get("think_trace") else ""
        result.append(ChatMessage(
            role="assistant",
            content=think_block + json.dumps(ex["intent_json"]),
        ))

    # Append the actual user query and any remaining messages
    result.extend(remaining)
    return result


def parse_llm_response(response: str) -> tuple[object | None, str]:
    """Parse LLM response, stripping <think> block, extracting IntentSpec JSON.

    Handles two output formats:
    1. Intent format: <think>...</think>\n{IntentSpec JSON} → returns (IntentSpec, raw)
    2. Query format: {"query": "..."} → returns (None, query_string)

    Returns:
        (intent, clean_response) — intent is None if not intent format
    """
    raw = response

    # Size guard: skip JSON parsing for very large responses (>10KB)
    if len(response) > 10240:
        return None, response

    # Strip <think>...</think> block
    think_end = response.find("</think>")
    if think_end >= 0:
        response = response[think_end + len("</think>"):].strip()

    # Try parsing as JSON
    try:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start < 0 or json_end <= json_start:
            return None, response

        data = json.loads(response[json_start:json_end])

        # Old format: {"query": "..."}
        if "query" in data and len(data) == 1:
            return None, data["query"]

        # New format: IntentSpec compact dict
        if IntentSpec is not None:
            intent = IntentSpec.from_compact_dict(data)
            if intent.has_content():
                return intent, raw
            # Empty intent — fall back
            return None, response

        return None, response
    except (json.JSONDecodeError, TypeError, ValueError):
        return None, response


async def _run_hybrid(
    messages: list[ChatMessage],
    nl_query: str,
    max_tokens: int = 256,
) -> tuple[Any, int, int]:
    """Run NER and NLS in parallel, merge results.

    When RAG is enabled, retrieves few-shot examples and field cards
    in parallel with NER, then augments the LLM prompt before generation.

    Returns:
        Tuple of (MergeResult, prompt_tokens, completion_tokens)
    """
    loop = asyncio.get_event_loop()

    # Run NER in parallel with RAG retrieval (both are fast, <20ms)
    ner_future = loop.run_in_executor(None, process_query, nl_query)

    rag_few_shot: list[dict] = []
    rag_cards: list[str] | None = None

    if RAG_ENABLED and retrieve_few_shot is not None:
        rag_future = loop.run_in_executor(None, retrieve_few_shot, nl_query, RAG_NUM_EXAMPLES)
        if select_cards is not None:
            cards_future = loop.run_in_executor(None, select_cards, nl_query, RAG_MAX_CARDS)
            ner_result, rag_few_shot, rag_cards = await asyncio.gather(
                ner_future, rag_future, cards_future
            )
        else:
            ner_result, rag_few_shot = await asyncio.gather(ner_future, rag_future)
    else:
        ner_result = await ner_future

    # Build augmented messages with few-shot examples and field cards
    augmented_messages = build_rag_messages(messages, rag_few_shot, rag_cards)

    # Run LLM with (potentially augmented) prompt, with timeout
    try:
        raw_response, p_tok, c_tok = await asyncio.wait_for(
            loop.run_in_executor(
                None, generate_query, augmented_messages, max_tokens, True
            ),
            timeout=LLM_TIMEOUT,
        )
    except asyncio.TimeoutError:
        print(f"[Hybrid] LLM timeout after {LLM_TIMEOUT}s, using NER-only")
        ner_query = ner_result.final_query if ner_result and ner_result.success else ""
        _log_telemetry(
            nl_query=nl_query, final_query=ner_query,
            source="ner_only_timeout", error="LLM timeout",
            latency_ms=(time.time() - time.time()),  # Will be reported by caller
        )
        ner_merge = MergeResult(
            query=ner_query,
            source="ner_only",
            nls_query="",
            ner_query=ner_query,
            confidence=ner_result.confidence if ner_result else 0.5,
            timing={"llm_timeout": True},
        )
        # Post-assembly: UAT augmentation on NER result
        if rewrite_abs_to_abs_or_uat is not None:
            ner_merge.query = rewrite_abs_to_abs_or_uat(ner_merge.query)
        if rewrite_abs_to_abs_or_planetary_feature is not None:
            ner_merge.query = rewrite_abs_to_abs_or_planetary_feature(ner_merge.query)
        return ner_merge, 0, 0

    # Parse LLM output — detect intent format vs query format
    llm_intent, clean_response = parse_llm_response(raw_response)

    if llm_intent is not None and merge_ner_and_nls_intent is not None:
        # New path: LLM output IntentSpec JSON directly
        merged = merge_ner_and_nls_intent(ner_result, llm_intent, nl_query)
        # Post-assembly: UAT augmentation (operates on final query string)
        if rewrite_abs_to_abs_or_uat is not None:
            merged.query = rewrite_abs_to_abs_or_uat(merged.query)
        if rewrite_abs_to_abs_or_planetary_feature is not None:
            merged.query = rewrite_abs_to_abs_or_planetary_feature(merged.query)
    else:
        # Old path: LLM output raw query string
        # Apply string-level post-processing before merge
        if rewrite_aff_to_inst_or_aff is not None:
            clean_response = rewrite_aff_to_inst_or_aff(clean_response)
        if rewrite_bibstem_values is not None:
            clean_response = rewrite_bibstem_values(clean_response)
        if rewrite_complex_author_wildcards is not None:
            clean_response = rewrite_complex_author_wildcards(clean_response)

        merged = merge_ner_and_nls(ner_result, clean_response, nl_query)

        # Post-assembly: UAT and planetary feature augmentation
        if rewrite_abs_to_abs_or_uat is not None:
            merged.query = rewrite_abs_to_abs_or_uat(merged.query)
        if rewrite_abs_to_abs_or_planetary_feature is not None:
            merged.query = rewrite_abs_to_abs_or_planetary_feature(merged.query)

    return merged, p_tok, c_tok


def _should_use_hybrid() -> bool:
    """Check if hybrid mode should be used (pipeline + model + merge available)."""
    return (
        HYBRID_MODE
        and PIPELINE_AVAILABLE
        and model is not None
        and merge_ner_and_nls is not None
    )


@app.on_event("startup")
async def startup():
    """Load model on startup."""
    load_model()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "device": DEVICE,
        "pipeline_available": PIPELINE_AVAILABLE,
        "hybrid_mode": _should_use_hybrid(),
        "rag_enabled": RAG_ENABLED,
    }


@app.get("/debug/pipeline")
async def debug_pipeline(q: str = "recent papers from cfa on the hubble tension"):
    """Debug endpoint: run pipeline directly, return result or error."""
    if not PIPELINE_AVAILABLE:
        return {"error": "Pipeline not available", "pipeline_available": False}
    try:
        result = process_query(q)
        return {
            "query": result.final_query,
            "intent": result.intent.__dict__ if hasattr(result, "intent") else {},
            "error": None,
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


@app.get("/debug/hybrid")
async def debug_hybrid(q: str = "recent papers from cfa on the hubble tension"):
    """Debug endpoint: run hybrid merge, return full details."""
    if not _should_use_hybrid():
        return {
            "error": "Hybrid mode not available",
            "hybrid_mode": HYBRID_MODE,
            "pipeline_available": PIPELINE_AVAILABLE,
            "model_loaded": model is not None,
        }
    try:
        messages = [
            ChatMessage(role="system", content=SYSTEM_PROMPT),
            ChatMessage(role="user", content=f"Query: {q}\nDate: {datetime.now().strftime('%Y-%m-%d')}"),
        ]
        start = time.time()
        merged, p_tok, c_tok = await _run_hybrid(messages, q)
        total_ms = (time.time() - start) * 1000
        return {
            "query": merged.query,
            "source": merged.source,
            "nls_query": merged.nls_query,
            "ner_query": merged.ner_query,
            "fields_injected": merged.fields_injected,
            "confidence": merged.confidence,
            "timing": {**merged.timing, "total_ms": total_ms},
            "prompt_tokens": p_tok,
            "completion_tokens": c_tok,
            # Intent traces for debugging merge decisions
            "intents": {
                "ner": merged.ner_intent,
                "llm": merged.llm_intent,
                "merged": merged.merged_intent,
            },
            # RAG context used
            "rag": {
                "enabled": RAG_ENABLED,
                "few_shot_count": len(_debug_few_shot) if (_debug_few_shot := (
                    retrieve_few_shot(q, RAG_NUM_EXAMPLES) if RAG_ENABLED and retrieve_few_shot else []
                )) else 0,
                "few_shot_examples": [
                    {"nl": ex["nl"], "intent_json": ex["intent_json"]}
                    for ex in _debug_few_shot
                ] if _debug_few_shot else [],
                "field_cards": select_cards(q, RAG_MAX_CARDS) if RAG_ENABLED and select_cards else [],
            },
        }
    except Exception as e:
        import traceback
        return {"error": str(e), "traceback": traceback.format_exc()}


@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "llm",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "adsabs",
            }
        ],
    }


def _extract_nl_query_from_messages(messages: list) -> str:
    """Extract natural language query from chat messages.

    Applies input sanitization:
    - Strips null bytes
    - Removes non-printable characters (keeps printable ASCII + common Unicode)
    - Truncates to 500 characters
    """
    user_message = next((m.content for m in messages if m.role == "user"), "")
    if "Query:" in user_message:
        query = user_message.split("Query:")[1].split("\n")[0].strip()
    else:
        query = user_message.strip()

    # Strip null bytes
    query = query.replace('\x00', '')

    # Strip non-printable characters (keep printable ASCII + common Unicode)
    query = ''.join(c for c in query if c.isprintable() or c in ('\n', '\t'))

    # Length limit
    if len(query) > 500:
        print(f"[Input] Query truncated from {len(query)} to 500 chars")
        query = query[:500]

    return query


@app.post("/v1/chat/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    """OpenAI-compatible chat completions endpoint (vLLM style).

    When hybrid mode is enabled, runs NER+NLS in parallel and merges results.
    When only pipeline is available (no model), uses NER-only.
    Falls back to the fine-tuned model if pipeline fails or is unavailable.
    """
    try:
        start_time = time.time()
        nl_query = _extract_nl_query_from_messages(request.messages)

        # Hybrid mode: run NER + NLS in parallel, merge results
        if _should_use_hybrid():
            try:
                # Check for ADS query passthrough
                if is_ads_query and is_ads_query(nl_query):
                    # Apply post-processing rewrites only
                    response_text = nl_query
                    if rewrite_aff_to_inst_or_aff:
                        response_text = rewrite_aff_to_inst_or_aff(response_text)
                    if rewrite_bibstem_values:
                        response_text = rewrite_bibstem_values(response_text)
                    if rewrite_complex_author_wildcards:
                        response_text = rewrite_complex_author_wildcards(response_text)
                    elapsed_ms = (time.time() - start_time) * 1000
                    print(f"[vLLM→Passthrough] ADS query in {elapsed_ms:.0f}ms: {response_text[:80]}...")
                    _log_telemetry(
                        nl_query=nl_query, final_query=response_text,
                        source="passthrough", latency_ms=elapsed_ms,
                    )
                    return ChatResponse(
                        id=f"chatcmpl-{int(time.time())}",
                        created=int(time.time()),
                        model=request.model,
                        choices=[ChatChoice(message=ChatMessage(role="assistant", content=response_text))],
                        usage=ChatUsage(),
                    )

                merged, p_tok, c_tok = await _run_hybrid(
                    request.messages, nl_query, request.max_tokens
                )
                elapsed_ms = (time.time() - start_time) * 1000
                print(f"[vLLM→Hybrid:{merged.source}] Generated in {elapsed_ms:.0f}ms: {merged.query[:80]}...")
                _log_telemetry(
                    nl_query=nl_query,
                    final_query=merged.query,
                    source=merged.source,
                    confidence=merged.confidence,
                    fields_injected=merged.fields_injected,
                    rag_enabled=RAG_ENABLED,
                    latency_ms=elapsed_ms,
                    merge_ms=merged.timing.get("merge_ms", 0),
                )
                return ChatResponse(
                    id=f"chatcmpl-{int(time.time())}",
                    created=int(time.time()),
                    model=request.model,
                    choices=[ChatChoice(message=ChatMessage(role="assistant", content=merged.query))],
                    usage=ChatUsage(
                        prompt_tokens=p_tok,
                        completion_tokens=c_tok,
                        total_tokens=p_tok + c_tok,
                    ),
                )
            except Exception as e:
                print(f"[vLLM→Hybrid] Error, falling back: {e}")

        # Non-hybrid: prefer pipeline when available
        if PIPELINE_AVAILABLE:
            try:
                result = process_query(nl_query)
                elapsed_ms = (time.time() - start_time) * 1000
                print(f"[vLLM→Pipeline] Generated in {elapsed_ms:.0f}ms: {result.final_query[:80]}...")
                _log_telemetry(
                    nl_query=nl_query, final_query=result.final_query,
                    source="ner_only", latency_ms=elapsed_ms,
                )
                return ChatResponse(
                    id=f"chatcmpl-{int(time.time())}",
                    created=int(time.time()),
                    model=request.model,
                    choices=[ChatChoice(message=ChatMessage(role="assistant", content=result.final_query))],
                    usage=ChatUsage(),
                )
            except Exception as e:
                print(f"[vLLM→Pipeline] Fallback to model: {e}")

        # Fallback to fine-tuned model only
        if model is None:
            raise HTTPException(status_code=503, detail="Model not loaded")

        response_text, prompt_tokens, completion_tokens = generate_query(
            request.messages, request.max_tokens
        )
        elapsed_ms = (time.time() - start_time) * 1000
        print(f"[vLLM] Generated in {elapsed_ms:.0f}ms: {response_text[:100]}...")
        _log_telemetry(
            nl_query=nl_query, final_query=response_text,
            source="nls_only", latency_ms=elapsed_ms,
        )

        return ChatResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request.model,
            choices=[ChatChoice(message=ChatMessage(role="assistant", content=response_text))],
            usage=ChatUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        print(f"[vLLM] Error: {e}")
        _log_telemetry(
            nl_query=nl_query if "nl_query" in dir() else "",
            final_query="", source="error",
            error=str(e),
            latency_ms=(time.time() - start_time) * 1000 if "start_time" in dir() else 0,
        )
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/pipeline", response_model=PipelineResponse)
@app.post("/", response_model=PipelineResponse)
async def pipeline_endpoint(request: PipelineRequest):
    """Hybrid NER+NLS pipeline endpoint.

    When hybrid mode is enabled, runs NER+NLS in parallel and merges.
    If only pipeline is available (no model), uses NER-only.
    Falls back to the fine-tuned model if pipeline fails.
    """
    try:
        # Extract user query from messages
        user_message = next(
            (m.content for m in request.messages if m.role == "user"), ""
        )

        # Parse query from "Query: X\nDate: Y" format
        nl_query = user_message
        if "Query:" in user_message:
            nl_query = user_message.split("Query:")[1].split("\n")[0].strip()

        start_time = time.time()

        # ADS query passthrough
        if PIPELINE_AVAILABLE and is_ads_query and is_ads_query(nl_query):
            response_text = nl_query
            if rewrite_aff_to_inst_or_aff:
                response_text = rewrite_aff_to_inst_or_aff(response_text)
            if rewrite_bibstem_values:
                response_text = rewrite_bibstem_values(response_text)
            if rewrite_complex_author_wildcards:
                response_text = rewrite_complex_author_wildcards(response_text)
            elapsed_ms = (time.time() - start_time) * 1000
            print(f"[Pipeline→Passthrough] ADS query in {elapsed_ms:.0f}ms: {response_text[:80]}...")
            _log_telemetry(
                nl_query=nl_query, final_query=response_text,
                source="passthrough", latency_ms=elapsed_ms,
            )
            return PipelineResponse(
                choices=[ChatChoice(message=ChatMessage(role="assistant", content=response_text))],
                pipeline_result=PipelineResult(
                    query=response_text,
                    debug_info=PipelineDebugInfo(total_time_ms=elapsed_ms, merge_source="passthrough"),
                ),
            )

        # Hybrid mode: run NER + NLS in parallel, merge results
        if _should_use_hybrid():
            try:
                merged, p_tok, c_tok = await _run_hybrid(
                    request.messages, nl_query, max_tokens=256
                )
                elapsed_ms = (time.time() - start_time) * 1000

                debug_info = PipelineDebugInfo(
                    nls_time_ms=merged.timing.get("nls_ms", 0),
                    merge_time_ms=merged.timing.get("merge_ms", 0),
                    total_time_ms=elapsed_ms,
                    merge_source=merged.source,
                    fields_injected=merged.fields_injected,
                    nls_query=merged.nls_query,
                    ner_query=merged.ner_query,
                )

                pipeline_result = PipelineResult(
                    query=merged.query,
                    debug_info=debug_info,
                    success=True,
                )

                print(f"[Pipeline→Hybrid:{merged.source}] Generated in {elapsed_ms:.0f}ms: {merged.query[:80]}")
                _log_telemetry(
                    nl_query=nl_query,
                    final_query=merged.query,
                    source=merged.source,
                    confidence=merged.confidence,
                    fields_injected=merged.fields_injected,
                    rag_enabled=RAG_ENABLED,
                    latency_ms=elapsed_ms,
                    merge_ms=merged.timing.get("merge_ms", 0),
                )

                return PipelineResponse(
                    choices=[ChatChoice(message=ChatMessage(role="assistant", content=merged.query))],
                    pipeline_result=pipeline_result,
                )
            except Exception as e:
                import traceback
                print(f"[Pipeline→Hybrid] Error, falling back: {e}")
                traceback.print_exc()

        # Non-hybrid: NER pipeline only
        if PIPELINE_AVAILABLE:
            try:
                result = process_query(nl_query)
                elapsed_ms = (time.time() - start_time) * 1000

                debug_info = PipelineDebugInfo(
                    ner_time_ms=result.debug_info.get("ner_time_ms", 0),
                    retrieval_time_ms=result.debug_info.get("retrieval_time_ms", 0),
                    assembly_time_ms=result.debug_info.get("assembly_time_ms", 0),
                    total_time_ms=elapsed_ms,
                    constraint_corrections=result.debug_info.get("constraint_corrections", []),
                    fallback_reason=result.debug_info.get("fallback_reason"),
                    merge_source="ner_only",
                    ner_query=result.final_query,
                )

                pipeline_result = PipelineResult(
                    query=result.final_query,
                    intent=result.intent.__dict__ if hasattr(result, 'intent') else {},
                    retrieved_examples=[],
                    debug_info=debug_info,
                    success=True,
                )

                print(f"[Pipeline→NER] Generated in {elapsed_ms:.0f}ms: {result.final_query}")
                _log_telemetry(
                    nl_query=nl_query, final_query=result.final_query,
                    source="ner_only", latency_ms=elapsed_ms,
                )

                return PipelineResponse(
                    choices=[ChatChoice(message=ChatMessage(role="assistant", content=result.final_query))],
                    pipeline_result=pipeline_result,
                )
            except Exception as e:
                import traceback
                print(f"[Pipeline→NER] Error, falling back to model: {e}")
                traceback.print_exc()

        # Fallback to fine-tuned model only
        response_text, _, _ = generate_query(request.messages, max_tokens=256)
        elapsed_ms = (time.time() - start_time) * 1000

        print(f"[Pipeline-Fallback] Generated in {elapsed_ms:.0f}ms: {response_text}")
        _log_telemetry(
            nl_query=nl_query, final_query=response_text,
            source="nls_only", latency_ms=elapsed_ms,
        )

        return PipelineResponse(
            choices=[ChatChoice(message=ChatMessage(role="assistant", content=response_text))],
            pipeline_result=PipelineResult(
                query=response_text,
                debug_info=PipelineDebugInfo(total_time_ms=elapsed_ms, merge_source="nls_only"),
            ),
            fallback=True,
        )

    except Exception as e:
        print(f"[Pipeline] Error: {e}")
        _log_telemetry(
            nl_query=nl_query if "nl_query" in dir() else "",
            final_query="", source="error",
            error=str(e),
            latency_ms=(time.time() - start_time) * 1000 if "start_time" in dir() else 0,
        )
        return PipelineResponse(
            choices=[],
            error=str(e),
        )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
