# shared/core/llama_backend.py

from llama_cpp import Llama


def load(
    model_path,
    n_ctx=4096,
    temperature=0.7,
    n_threads=4,
    n_gpu_layers=0,
):
    """
    Lädt ein GGUF-Modell via llama.cpp und wrapped es in ein Dict,
    damit der backend_router es unterscheiden kann.
    """
    inst = Llama(
        model_path=model_path,
        n_ctx=n_ctx,
        logits_all=False,
        embedding=False,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
        verbose=False,
    )

    return {
        "backend": "llama",
        "instance": inst,
        "n_ctx": n_ctx,
        "temperature": temperature,
    }


def stream_chat(llm, messages, perf=None):
    """
    ECHTES Streaming über llama_cpp.create_chat_completion(stream=True)
    → gibt NUR Strings zurück (keine Dicts mehr).
    """
    perf = perf or {}
    inst: Llama = llm["instance"]

    temperature = float(perf.get("temperature", llm.get("temperature", 0.7)))
    top_p = float(perf.get("top_p", 0.9))

    stream = inst.create_chat_completion(
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        stream=True,
    )

    for token in stream:
        if "choices" not in token:
            continue
        delta = token["choices"][0].get("delta", {})
        chunk = delta.get("content", "")
        if not chunk:
            continue
        # WICHTIG: immer String
        yield chunk