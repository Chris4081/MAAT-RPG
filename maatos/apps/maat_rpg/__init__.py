def start_classic():
    """
    Startet die MAAT-KI Classic-App:
    - Profile laden (classic.json, sonst Minimal)
    - Lokales GGUF-Modell wählen
    - Chat-Loop mit Streaming & Plugins
    """
    init(autoreset=True)
    print(Fore.GREEN + "🌿 MAAT-KI Classic wird gestartet …\n" + Style.RESET_ALL)

    # -------------------------------------------------
    # Profile laden
    # -------------------------------------------------
    profile_loader = ProfileLoader(ROOT)
    try:
        profile = profile_loader.load_profile("classic.json")
        print(Fore.GREEN + "✅ Profil geladen: classic.json\n" + Style.RESET_ALL)
    except Exception as e:
        print(Fore.RED + f"⚠ Profil-Fehler (classic.json): {e}" + Style.RESET_ALL)
        print(Fore.YELLOW + "→ Nutze Minimal-Systemprompt.\n" + Style.RESET_ALL)

        profile = {
            "systemprompt": (
                "Du bist MAAT-KI Classic — eine ethische, reflektierende KI, "
                "die nach Harmonie, Balance, Schöpfungskraft, Verbundenheit "
                "und Respekt antwortet. Sei ruhig, klar und hilfreich. 🌿"
            )
        }

    system_prompt = profile.get("systemprompt", "")

    # -------------------------------------------------
    # Plugin-System (App + Shared)
    # -------------------------------------------------
    APP_ROOT = os.path.dirname(__file__)
    app_plugin_root = os.path.join(APP_ROOT, "plugins")
    shared_plugin_root = os.path.join(ROOT, "shared", "plugins")

    pm = None
    if PluginManager is not None:
        try:
            print("APP_PLUGIN_ROOT =", app_plugin_root)
            print("SHARED_PLUGIN_ROOT =", shared_plugin_root)
            print("Ordner in shared/plugins:", os.listdir(shared_plugin_root))
            print("Ordner in app/plugins:", os.listdir(app_plugin_root))

            # PluginManager initialisieren und Plugins laden
            pm = PluginManager([app_plugin_root, shared_plugin_root])
            pm.load_plugins()

        except Exception as e:
            print(Fore.RED + f"⚠ Plugin-Fehler: {e}" + Style.RESET_ALL)
            pm = None
    else:
        print(Fore.YELLOW + "🔌 Plugin-System derzeit deaktiviert.\n" + Style.RESET_ALL)

    # -------------------------------------------------
    # Plugin Startup-Routinen aufrufen
    # -------------------------------------------------
    if pm is not None:
        for plugin in pm.iter_all_plugins():
            on_start = getattr(plugin, "on_startup", None)
            if callable(on_start):
                try:
                    on_start()
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN STARTUP ERROR] {e}" + Style.RESET_ALL)

    # -------------------------------------------------
    # Modell & Performance
    # -------------------------------------------------
    model_path = choose_model(MODEL_DIR)
    perf = choose_performance()
    llm = load_llm(model_path, perf)

    # -------------------------------------------------
    # Conversation + Memory beim Start laden
    # -------------------------------------------------
    conversation = [{"role": "system", "content": system_prompt}]
    print(Fore.CYAN + "📘 Nutze /hilfe um weitere Befehle kennenzulernen.\n" + Style.RESET_ALL)

    # Memory-Plugin finden (z.B. MAAT-Memory-Orchestrator)
    memory_plugin = None
    if pm is not None:
        for p in pm.iter_all_plugins():
            if getattr(p, "is_memory_plugin", False):
                memory_plugin = p
                break

    if memory_plugin and hasattr(memory_plugin, "db"):
        try:
            recent = memory_plugin.db[-40:]
        except Exception:
            recent = []

        print(
            Fore.GREEN
            + f"🧠 MAAT-Memory-Orchestrator gefunden – {len(recent)} Episoden geladen.\n"
            + Style.RESET_ALL
        )

        for m in recent:
            role = m.get("role")
            content = m.get("content")
            if role in ("user", "assistant") and content:
                conversation.append({"role": role, "content": content})
    else:
        print(
            Fore.YELLOW
            + "Kein Memory-Plugin gefunden oder DB leer.\n"
            + Style.RESET_ALL
        )

    # -------------------------------------------------
    # CHAT-LOOP
    # -------------------------------------------------
    while True:
        try:
            user_input = input(Fore.YELLOW + "> " + Style.RESET_ALL).strip()
            if not user_input:
                continue

            # EXIT
            if user_input.lower() in ("/exit", "/quit"):
                print(Fore.GREEN + "\n🌿 MAAT-KI Classic verabschiedet sich harmonisch. 🕊️\n")
                break

            # --------------------------------------------
            # BEFORE-HOOK (Plugin-Befehle & Interception)
            # --------------------------------------------
            reply = None
            turn_context = {
                "pm": pm,
                "profile_loader": profile_loader,
                "conversation": conversation,
                "llm": llm,
                "last_user_input": user_input,
            }

            if pm is not None:
                try:
                    handled, output = pm.handle_before_chat(
                        user_input,
                        context=turn_context,
                    )

                    if handled:
                        if output:
                            print(output)
                        continue  # 🔑 Modell NICHT mehr aufrufen

                    user_input = output

                except Exception as e:
                    print(Fore.RED + f"[PLUGIN BEFORE ERROR] {e}" + Style.RESET_ALL)

            # --------------------------------------------
            # MODEL CALL
            # --------------------------------------------
            conversation.append({"role": "user", "content": user_input})
            turn_context["conversation"] = conversation
            use_final_guard = bool(pm and pm.has_before_final_response(turn_context))

            stream_plugins = [] if use_final_guard else (pm.get_streaming_plugins() if pm else [])
            generator = stream_chat_completion(llm, conversation, perf, stream_plugins)

            reply = stream_to_console(generator, echo=not use_final_guard)
            original_reply = reply or ""

            # --------------------------------------------
            # AFTER-HOOK (Antwort verändern)
            # --------------------------------------------
            if reply is not None and pm is not None:
                try:
                    reply = pm.handle_after_response(
                        reply,
                        context=turn_context,
                    )
                    if use_final_guard:
                        reply = pm.handle_before_final_response(reply, turn_context)
                except Exception as e:
                    print(Fore.RED + f"[PLUGIN AFTER ERROR] {e}" + Style.RESET_ALL)

            if use_final_guard:
                if isinstance(reply, str) and reply.strip():
                    from shared.core.streaming import stream_text_to_console
                    stream_text_to_console(reply)
                if pm is not None:
                    pm.handle_after_final_response(reply, turn_context)
            elif reply != original_reply:
                extra = reply[len(original_reply):]
                if extra.strip():
                    print(extra)

            # --------------------------------------------
            # SPEICHERN
            # --------------------------------------------
            conversation.append({"role": "assistant", "content": reply})

        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\n🌿 Abbruch per Strg+C — bis bald!\n")
            break

        except Exception as e:
            print(Fore.RED + f"\n⚠ Unerwarteter Fehler im Chat-Loop: {e}\n")
            continue
