# shared/core/backend_router.py

def load_backend(
    model_path,
    backend="auto",
    max_ctx=4096,
    temperature=0.7,
    n_threads=4,
    n_gpu_layers=0,
):
    """
    Router für alle Backends:
    - backend="mlx"   → nur MLX
    - backend="llama" → nur llama.cpp
    - backend="auto"  → erst llama.cpp, bei Fehler fallback auf MLX
    """

    mlx_kwargs = dict(
        max_ctx=max_ctx,
        temperature=temperature,
    )

    llama_kwargs = dict(
        n_ctx=max_ctx,
        temperature=temperature,
        n_threads=n_threads,
        n_gpu_layers=n_gpu_layers,
    )

    # -------------------------------
    # Forced MLX
    # -------------------------------
    if backend == "mlx":
        from .mlx_backend import load as mlx_load
        return mlx_load(model_path, **mlx_kwargs)

    # -------------------------------
    # Forced llama.cpp
    # -------------------------------
    if backend == "llama":
        from .llama_backend import load as llama_load
        return llama_load(model_path, **llama_kwargs)

    # -------------------------------
    # AUTO → try MLX → fallback CPU
    # -------------------------------

    try:
        from .llama_backend import load as llama_load
        return llama_load(model_path, **llama_kwargs)
    except Exception as e:
        print(f"[AUTO] llama failed -> MLX fallback\n{e}")
        from .mlx_backend import load as mlx_load
        return mlx_load(model_path, **mlx_kwargs)


# ---- Helper: Messages → Prompt für MLX ----
def _build_prompt_from_messages(messages):
    parts = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")

        if role == "system":
            prefix = "[System]"
        elif role == "assistant":
            prefix = "Assistant:"
        else:
            prefix = "User:"

        parts.append(f"{prefix} {content}")

    parts.append("Assistant:")
    return "\n".join(parts)


def stream_chat(llm, messages, perf=None):
    perf = perf or {}

    backend = None
    if isinstance(llm, dict):
        backend = llm.get("backend", "mlx")
    else:
        backend = "llama"

    if backend == "mlx":
        from .mlx_backend import stream_chat as mlx_stream
        prompt = _build_prompt_from_messages(messages)
        max_tokens = perf.get("max_tokens", 512)
        return mlx_stream(llm, prompt, max_tokens=max_tokens)

    from .llama_backend import stream_chat as llama_stream
    return llama_stream(llm, messages, perf)