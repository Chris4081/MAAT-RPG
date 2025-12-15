# shared/core/mlx_backend.py

from mlx_lm import load as mlx_load, stream_generate


def load(model_path, max_ctx: int = 4096, temperature: float = 0.7):
    """
    Lädt ein MLX-Modell über mlx_lm.load und packt es in ein LLM-Dict,
    das der backend_router versteht.
    """
    model, tokenizer = mlx_load(model_path)

    return {
        "backend": "mlx",
        "model": model,
        "tokenizer": tokenizer,
        "max_ctx": max_ctx,
        "temperature": temperature,
    }


def stream_chat(llm: dict, prompt: str, max_tokens: int = 512):
    """
    Streaming-Chat für MLX-Modelle.
    Nutzt stream_generate(model, tokenizer, prompt, max_tokens=...).

    Die Funktion liefert **Strings** (resp.text), damit deine
    Streaming-Engine einfach `full += chunk` machen kann.
    """
    model = llm["model"]
    tokenizer = llm["tokenizer"]

    # Temperatur könntest du später über einen eigenen Sampler einbauen;
    # für jetzt nehmen wir die Defaults von mlx-lm.
    for response in stream_generate(
        model,
        tokenizer,
        prompt,
        max_tokens=max_tokens,
    ):
        text = getattr(response, "text", None)
        if not text:
            continue
        # Sicherstellen, dass wirklich ein String rausgeht
        yield text