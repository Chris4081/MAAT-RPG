"""Actionable model-loading messages without exposing a traceback as game text."""
MODEL_LOAD_MESSAGE = 'Modell kann nicht geladen werden. Prüfe dein System.'

EN = {
    MODEL_LOAD_MESSAGE: 'The model cannot be loaded. Please check your system.',
    'Nicht genug Arbeitsspeicher zum Laden des Modells.': 'There is not enough RAM to load the model.',
    'Wähle eine kleinere GGUF-Datei oder einen kleineren Kontext und schließe andere speicherintensive Programme.': 'Choose a smaller GGUF file or a shorter context and close other memory-intensive programs.',
    'Die Modelldatei kann nicht gelesen werden.': 'The model file cannot be read.',
    'Prüfe die Zugriffsrechte oder wähle eine lesbare Kopie der GGUF-Datei.': 'Check file permissions or choose a readable copy of the GGUF file.',
    'Die gespeicherte Modelldatei wurde nicht gefunden.': 'The saved model file was not found.',
    'Wähle die GGUF-Datei erneut aus; möglicherweise wurde sie verschoben oder das Laufwerk ist nicht verbunden.': 'Select the GGUF file again; it may have moved or its drive may be disconnected.',
    'Die Modelldatei ist ungültig oder möglicherweise unvollständig.': 'The model file is invalid or may be incomplete.',
    'Wähle eine vollständige GGUF-Datei. Bei einem Downloadfehler lade das Modell erneut herunter.': 'Choose a complete GGUF file. If the download failed, download the model again.',
    'Dieses Modellformat wird von der installierten KI-Laufzeit nicht unterstützt.': 'This model format is not supported by the installed AI runtime.',
    'Wähle ein kompatibles GGUF-Chatmodell; eventuell benötigt dieses Modell eine neuere llama.cpp-Version.': 'Choose a compatible GGUF chat model; this model may require a newer llama.cpp version.',
    'Das Modell konnte nicht geladen werden.': 'The model could not be loaded.',
    'Du kannst es erneut versuchen oder eine andere GGUF-Datei auswählen.': 'You can try again or select a different GGUF file.',
}


def process_exit_error(language='de'):
    if language == 'en':
        return EN[MODEL_LOAD_MESSAGE]+'\n\nThe AI process exited unexpectedly while loading.\nPossible causes include memory exhaustion or a model library error. The game connection is being restored without a model. Choose a smaller or different model.'
    return MODEL_LOAD_MESSAGE+'\n\nDer KI-Prozess wurde beim Laden unerwartet beendet.\nMögliche Ursachen sind Speichermangel oder ein Fehler der Modellbibliothek. Die Spielverbindung wird ohne Modell wiederhergestellt. Wähle anschließend ein kleineres oder anderes Modell.'

def load_error(exc, language='de'):
    from shared.core.model_safety import ModelSafetyError, safety_message
    if isinstance(exc, ModelSafetyError):
        return safety_message(exc, language), str(exc.report or exc.reason)
    detail=str(exc).strip() or type(exc).__name__
    text=detail.casefold()
    if isinstance(exc,MemoryError) or any(x in text for x in ('out of memory','failed to allocate','cannot allocate','insufficient memory')):
        message='Nicht genug Arbeitsspeicher zum Laden des Modells.'
        action='Wähle eine kleinere GGUF-Datei oder einen kleineren Kontext und schließe andere speicherintensive Programme.'
    elif isinstance(exc,PermissionError):
        message='Die Modelldatei kann nicht gelesen werden.'
        action='Prüfe die Zugriffsrechte oder wähle eine lesbare Kopie der GGUF-Datei.'
    elif isinstance(exc,FileNotFoundError) or any(x in text for x in ('vorhandene gguf','no such file','not found')):
        message='Die gespeicherte Modelldatei wurde nicht gefunden.'
        action='Wähle die GGUF-Datei erneut aus; möglicherweise wurde sie verschoben oder das Laufwerk ist nicht verbunden.'
    elif any(x in text for x in ('gültige gguf','invalid gguf','invalid magic','unexpected end','failed to read')):
        message='Die Modelldatei ist ungültig oder möglicherweise unvollständig.'
        action='Wähle eine vollständige GGUF-Datei. Bei einem Downloadfehler lade das Modell erneut herunter.'
    elif any(x in text for x in ('unsupported','unknown model architecture','not supported')):
        message='Dieses Modellformat wird von der installierten KI-Laufzeit nicht unterstützt.'
        action='Wähle ein kompatibles GGUF-Chatmodell; eventuell benötigt dieses Modell eine neuere llama.cpp-Version.'
    else:
        message='Das Modell konnte nicht geladen werden.'
        action='Du kannst es erneut versuchen oder eine andere GGUF-Datei auswählen.'
    title=MODEL_LOAD_MESSAGE
    if language=='en':
        title,message,action=(EN[t] for t in (title,message,action))
    return title+'\n\n'+message+'\n'+action,detail
