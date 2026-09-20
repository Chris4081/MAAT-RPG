# -*- coding: utf-8 -*-
"""
Tool: find_context_errors.py
----------------------------------------
Scannt alle Plugins und sucht Zugriffe auf:
  - context["conversation"]
  - context.get("conversation")
Markiert, ob der Zugriff sicher oder gefährlich ist.
"""

import os
import re

PLUGIN_ROOT = "shared/plugins"

print("🔍 Scanne Plugin-Ordner auf unsichere Context-Zugriffe…\n")

danger_patterns = [
    r'context\["conversation"\]',
    r"context\['conversation'\]",
]

safe_patterns = [
    r'context\.get\("conversation"\)',
    r"context\.get\('conversation'\)",
]

results = []

for root, dirs, files in os.walk(PLUGIN_ROOT):
    for f in files:
        if not f.endswith(".py"):
            continue

        path = os.path.join(root, f)

        with open(path, "r", encoding="utf-8") as fp:
            text = fp.read()

        # Suche unsichere Zugriffe
        found_danger = any(re.search(p, text) for p in danger_patterns)
        found_safe   = any(re.search(p, text) for p in safe_patterns)

        if found_danger:
            results.append((path, "⚠️ UNSICHER – benutzt context['conversation']!!"))

        elif found_safe:
            results.append((path, "✅ sicher – benutzt context.get()"))

        else:
            # Kein Zugriff → neutral
            results.append((path, "• kein conversation-Zugriff"))

print("📦 Ergebnis:\n")
for path, status in results:
    print(f"{status:50}  →  {path}")

print("\n✨ Scan abgeschlossen.")