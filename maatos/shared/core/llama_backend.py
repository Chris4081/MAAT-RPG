# shared/core/llama_backend.py

from llama_cpp import Llama

from .thinking_mode import chat_completion_thinking_kwargs
from .gguf_chat import configure_template, normalize_channels


def load(
    model_path,
    n_ctx=20000,
    temperature=0.7,
    n_threads=4,
    n_gpu_layers=0,
    load_options=None,
    allow_cpu_fallback=True,
):
    """
    Lädt ein GGUF-Modell via llama.cpp und wrapped es in ein Dict,
    damit der backend_router es unterscheiden kann.
    """
    # Gemma's mixed attention dimensions otherwise require padded V caches.
    gemma4 = 'gemma-4' in str(model_path).lower() or 'gemma4' in str(model_path).lower()
    compatibility = dict(flash_attn=True, n_batch=128, n_ubatch=64) if gemma4 else {}
    if load_options:
        compatibility.update(load_options)
    kwargs = dict(model_path=model_path, n_ctx=n_ctx, logits_all=False, embedding=False,
                  n_threads=n_threads, n_gpu_layers=n_gpu_layers, verbose=False, **compatibility)
    fallback = None
    try:
        inst = Llama(**kwargs)
    except (ValueError, RuntimeError) as exc:
        if not allow_cpu_fallback or load_options is None or n_gpu_layers == 0 or not any(word in str(exc).lower() for word in ('context', 'alloc', 'memory', 'gpu', 'metal', 'cuda', 'backend')):
            raise
        # GPU capability in the library does not guarantee a usable device or enough VRAM.
        import gc
        gc.collect()
        fallback = str(exc)
        kwargs.update(n_gpu_layers=0, n_batch=128, n_ubatch=64, flash_attn=gemma4,
                      offload_kqv=False, op_offload=False)
        inst = Llama(**kwargs)

    try:
        chat_state = configure_template(inst)
    except Exception:
        inst.close()
        raise

    return {
        "load_settings": {k:v for k,v in kwargs.items() if k != "model_path"},
        "hardware_fallback": fallback,
        "chat_state": chat_state,
        "backend": "llama",
        "instance": inst,
        "n_ctx": n_ctx,
        "temperature": temperature,
    }


def stream_chat(llm, messages, perf=None):
    """Keep the model loaded after Esc, including cancellation during prefill."""
    turn = (perf or {}).get('_chat_turn')
    inst = llm['instance']
    callback = None
    api = None
    ctx = getattr(getattr(inst, '_ctx', None), 'ctx', None)
    source = None
    try:
        if turn:
            turn.check()
            from llama_cpp import llama_cpp as api
            if ctx and hasattr(api, 'llama_set_abort_callback'):
                callback = api.ggml_abort_callback(lambda _: turn.cancelled.is_set())
                api.llama_set_abort_callback(ctx, callback, None)
        source = _stream_chat(llm, messages, perf)
        for token in source:
            if turn: turn.check()
            yield token
        if turn: turn.check()
    except Exception:
        if turn: turn.check()  # llama_decode's aborted status is not a model failure.
        raise
    finally:
        if source is not None:
            source.close()
        if callback is not None:
            api.llama_set_abort_callback(ctx, api.ggml_abort_callback(), None)
        if turn and turn.cancelled.is_set():
            inst.reset()


def _stream_chat(llm, messages, perf=None):
    """
    ECHTES Streaming über llama_cpp.create_chat_completion(stream=True)
    → gibt NUR Strings zurück (keine Dicts mehr).
    """
    perf = perf or {}
    inst: Llama = llm["instance"]

    if str(getattr(inst, 'metadata', {}).get('general.architecture', '')).startswith('gemma4'):
        # Start each request with a fresh logical cache; history remains in messages.
        inst.reset()
    temperature = float(perf.get("temperature", llm.get("temperature", 0.7)))
    top_p = float(perf.get("top_p", 0.9))

    kwargs = dict(
        messages=messages,
        temperature=temperature,
        top_p=top_p,
        stream=True,
    )
    if 'max_tokens' in perf:
        maximum = perf['max_tokens']
        kwargs['max_tokens'] = max(1, int(maximum)) if maximum is not None else None
    if llm.get('chat_state', {}).get('family') != 'gpt-oss':
        kwargs.update(chat_completion_thinking_kwargs(getattr(inst, "create_chat_completion", None)))

    if llm.get('chat_state', {}).get('family') == 'gpt-oss':
        turn = perf.get('_chat_turn')
        stream = inst.chat_handler(llama=inst, cancel_check=turn.check if turn else None, **kwargs)
    else:
        stream = inst.create_chat_completion(**kwargs)

    def chunks():
        first = True
        for token in stream:
            choices = token.get("choices") or []
            if not choices:
                continue
            chunk = choices[0].get("delta", {}).get("content", "")
            if not chunk:
                continue
            if first:
                first = False
                if llm.get("chat_state", {}).get("thinking_prefix"):
                    yield "<think>"
            yield chunk
    try:
        if llm.get("chat_state", {}).get("architecture", "").startswith("gemma4"):
            yield from normalize_channels(chunks())
        elif llm.get('chat_state', {}).get('family') == 'mistral':
            yield from normalize_channels(chunks(), mistral=True)
        else:
            yield from chunks()
    finally:
        close = getattr(stream, 'close', None)
        if close: close()
