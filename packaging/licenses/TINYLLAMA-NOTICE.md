# TinyLlama Chat v1.0 template / Chatvorlage

The `CHAT_V1_TEMPLATE` constant in
[`maatos/shared/core/tinyllama.py`](../../maatos/shared/core/tinyllama.py)
contains the `chat_template` value from the TinyLlama project's
[TinyLlama-1.1B-Chat-v1.0 tokenizer configuration](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0/blob/main/tokenizer_config.json).
The [model repository](https://huggingface.co/TinyLlama/TinyLlama-1.1B-Chat-v1.0)
identifies its license as Apache-2.0. A full copy is included in
[Apache-2.0.txt](Apache-2.0.txt).

MAAT RPG extracts the template from JSON and embeds it as a Python string in its
own compatibility module. The model detection and fallback integration around
that string are MAAT RPG code. This attribution applies to the template;
it does not relicense the entire module or distribute model weights.

Deutsch: Die Konstante stammt aus der oben verlinkten TinyLlama-Chatvorlage unter
Apache-2.0. Das RPG übernimmt den JSON-Wert als Python-Zeichenkette und ergänzt
eine eigene Modellerkennung und Ersatzlogik. Die Lizenzzuordnung gilt für diese
Vorlage; Modellgewichte werden nicht mitgeliefert.
