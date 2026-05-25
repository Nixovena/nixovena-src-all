import sys
import os
import argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from core import (
    C, banner, box, prompt, ok, warn, err, info, row, dim, clear, pause,
    Config, Session, build_ai, AIError, list_ollama_models, CONFIG_PATH, personas,
)
from modules import REGISTRY, OSINT_MODULES, AI_MODULES
from modules import (
    username, email, domain, ip, phone, breach,
    image, crypto, social, ai_auto,
)


CLI_DISPATCHERS = {
    "username": username.dispatch,
    "email":    email.dispatch,
    "domain":   domain.dispatch,
    "ip":       ip.dispatch,
    "phone":    phone.dispatch,
    "breach":   breach.dispatch,
    "image":    image.dispatch,
    "crypto":   crypto.dispatch,
    "social":   social.dispatch,
}


class AppCtx:
    def __init__(self, cfg):
        self.cfg = cfg
        self.session = Session(cfg.options.get("results_dir", str(Path.home() / "almighty-osint-results")))
        self.ai = None
        self._init_ai()

    def _init_ai(self):
        try:
            self.ai = build_ai(self.cfg)
            if not self.ai.available():
                warn(f"AI backend '{self.ai.name}' is not reachable; AI features disabled until configured.")
                self.ai = None
        except AIError as e:
            warn(f"AI init failed: {e}")
            self.ai = None


def settings_menu(ctx):
    while True:
        clear()
        banner()
        box("Settings", C.BR_BLU)
        a = ctx.cfg.ai
        k = ctx.cfg.api_keys
        row("1. AI backend",          a.get("backend"))
        row("2. AI model (chat)",     a.get("model"))
        row("3. Vision model",        a.get("vision_model"))
        row("4. Embedding model",     a.get("embed_model"))
        row("5. Persona",             a.get("persona"))
        row("6. Streaming output",    "on" if a.get("stream") else "off")
        row("7. Ollama host",         a.get("ollama_host"))
        row("8. OpenAI base URL",     a.get("openai_base_url"))
        row("9. OpenAI API key",      "(set)" if a.get("openai_api_key") else "(empty)")
        row("10. Anthropic API key",  "(set)" if a.get("anthropic_api_key") else "(empty)")
        row("11. Local model path",   a.get("local_model_path") or "(empty)")
        row("12. Temperature",        str(a.get("temperature")))
        row("13. Max tokens",         str(a.get("max_tokens")))
        print()
        row("20. HIBP key",           "(set)" if k.get("hibp") else "(empty)")
        row("21. Shodan key",         "(set)" if k.get("shodan") else "(empty)")
        row("22. AbuseIPDB key",      "(set)" if k.get("abuseipdb") else "(empty)")
        row("23. Hunter key",         "(set)" if k.get("hunter") else "(empty)")
        row("24. Etherscan key",      "(set)" if k.get("etherscan") else "(empty)")
        row("25. Numverify key",      "(set)" if k.get("numverify") else "(empty)")
        print()
        row("L. List Ollama models",  "")
        row("R. Re-test AI backend",  "")
        row("P. Pick persona",        f"current: {a.get('persona')}")
        row("0. Back",                "")
        print(f"\n  {C.DIM}Config file: {CONFIG_PATH}{C.RESET}\n")
        c = prompt("Pick", "0").lower()

        if c == "0":
            return
        if c == "l":
            models = list_ollama_models(a.get("ollama_host", "http://127.0.0.1:11434"))
            if not models:
                warn("No models found / Ollama not reachable")
            else:
                ok(f"{len(models)} model(s):")
                for m in models:
                    print(f"    {C.CYAN}- {m}{C.RESET}")
            pause(); continue
        if c == "r":
            ctx._init_ai()
            if ctx.ai:
                ok(f"AI ready: {ctx.ai.name}/{ctx.ai.model}")
                caps = ctx.ai.capabilities
                row("Capabilities", f"chat={caps.get('chat')}, stream={caps.get('stream')}, embed={caps.get('embed')}, vision={caps.get('vision')}")
            pause(); continue
        if c == "p":
            print(f"\n  {C.BOLD}Available personas:{C.RESET}")
            for n in personas.names():
                marker = "*" if n == a.get("persona") else " "
                print(f"  {marker} {C.CYAN}{n}{C.RESET}")
            pn = prompt("Persona name", a.get("persona","analyst")).lower().strip()
            if pn in personas.PERSONAS:
                ctx.cfg.set("ai.persona", pn); ctx.cfg.save()
                ok(f"Persona: {pn}")
            else:
                warn("Unknown persona")
            pause(); continue

        mapping = {
            "1":  ("ai.backend",            "Backend (ollama|openai|anthropic|local|groq|openrouter)"),
            "2":  ("ai.model",              "Chat model name"),
            "3":  ("ai.vision_model",       "Vision model name (e.g. llava, gpt-4o)"),
            "4":  ("ai.embed_model",        "Embedding model (e.g. nomic-embed-text, text-embedding-3-small)"),
            "5":  ("ai.persona",            f"Persona ({', '.join(personas.names())})"),
            "6":  ("ai.stream",             "Streaming output (true/false)"),
            "7":  ("ai.ollama_host",        "Ollama host URL"),
            "8":  ("ai.openai_base_url",    "OpenAI-compatible base URL"),
            "9":  ("ai.openai_api_key",     "OpenAI API key"),
            "10": ("ai.anthropic_api_key",  "Anthropic API key"),
            "11": ("ai.local_model_path",   "Path to GGUF model"),
            "12": ("ai.temperature",        "Temperature (0.0-2.0)"),
            "13": ("ai.max_tokens",         "Max tokens"),
            "20": ("api_keys.hibp",         "HIBP key"),
            "21": ("api_keys.shodan",       "Shodan key"),
            "22": ("api_keys.abuseipdb",    "AbuseIPDB key"),
            "23": ("api_keys.hunter",       "Hunter.io key"),
            "24": ("api_keys.etherscan",    "Etherscan key"),
            "25": ("api_keys.numverify",    "Numverify key"),
        }
        if c in mapping:
            key, label = mapping[c]
            cur = ctx.cfg.get(key, "")
            new = prompt(f"{label}", str(cur))
            if key == "ai.temperature":
                try:    new = float(new)
                except: new = 0.4
            elif key == "ai.max_tokens":
                try:    new = int(new)
                except: new = 2048
            elif key == "ai.stream":
                new = str(new).lower() in ("1","true","yes","on","y")
            ctx.cfg.set(key, new)
            ctx.cfg.save()
            ok("Saved")
            pause()
        else:
            warn("Unknown option")
            pause()


def _ai_status_line(ctx):
    if not ctx.ai:
        return f"  {C.RED}● AI: not configured (Settings -> 1){C.RESET}"
    caps = ctx.ai.capabilities
    flags = []
    if caps.get("stream"): flags.append("stream")
    if caps.get("embed"):  flags.append("embed")
    if caps.get("vision"): flags.append("vision")
    cap_str = ",".join(flags) or "chat"
    persona = ctx.cfg.ai.get("persona","analyst")
    return f"  {C.GREEN}● AI: {ctx.ai.name}/{ctx.ai.model}  [{cap_str}]  persona={persona}{C.RESET}"


def main_menu(ctx):
    while True:
        clear()
        banner()
        print(_ai_status_line(ctx))
        print(f"  {C.DIM}Session: {ctx.session.id}  |  Findings: {len(ctx.session.findings)}  |  Dir: {ctx.session.results_dir}{C.RESET}\n")

        print(f"  {C.BOLD}{C.BR_CYN}── OSINT MODULES ──{C.RESET}")
        for i, (name, _) in enumerate(OSINT_MODULES, 1):
            print(f"  {C.CYAN}{i:>2}.{C.RESET} {name}")

        offset = len(OSINT_MODULES)
        print(f"\n  {C.BOLD}{C.BR_MAG}── AI MODULES ──{C.RESET}")
        for i, (name, _) in enumerate(AI_MODULES, 1):
            print(f"  {C.MAGENTA}{i+offset:>2}.{C.RESET} {name}")

        print()
        print(f"  {C.BR_BLU} S.{C.RESET} Settings & API Keys")
        print(f"  {C.BR_BLU} P.{C.RESET} Switch persona ({ctx.cfg.ai.get('persona')})")
        print(f"  {C.BR_BLU} E.{C.RESET} Export session (JSON + Markdown)")
        print(f"  {C.BR_BLU} N.{C.RESET} New session")
        print(f"  {C.RED} 0.{C.RESET} Exit\n")

        try:
            c = input(f"  {C.YELLOW}Pick [0-{len(REGISTRY)}/S/P/E/N]:{C.RESET} ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print()
            return

        if c == "0":
            return
        if c == "s":
            settings_menu(ctx); ctx._init_ai(); continue
        if c == "p":
            print(f"\n  {C.BOLD}Personas:{C.RESET}")
            for n in personas.names():
                marker = "*" if n == ctx.cfg.ai.get("persona") else " "
                print(f"  {marker} {C.CYAN}{n}{C.RESET}")
            pn = prompt("Pick persona", ctx.cfg.ai.get("persona","analyst")).lower().strip()
            if pn in personas.PERSONAS:
                ctx.cfg.set("ai.persona", pn); ctx.cfg.save()
                ok(f"Persona: {pn}")
            else:
                warn("Unknown persona")
            pause(); continue
        if c == "e":
            j = ctx.session.export("json"); m = ctx.session.export("md")
            ok(f"Exported: {j}"); ok(f"Exported: {m}")
            pause(); continue
        if c == "n":
            ctx.session = Session(ctx.cfg.options.get("results_dir"))
            ok(f"New session: {ctx.session.id}")
            pause(); continue

        try:
            idx = int(c) - 1
        except Exception:
            warn("Invalid choice"); pause(); continue
        if 0 <= idx < len(REGISTRY):
            try:
                REGISTRY[idx][1](ctx)
            except KeyboardInterrupt:
                print(f"\n  {C.YELLOW}Module cancelled{C.RESET}")
            except Exception as e:
                err(f"Module error: {e}")
            pause()
        else:
            warn("Out of range"); pause()


CLI_AI_FLOW = {
    "auto":     ai_auto.run,
}


def cli_run(ctx, args):
    mod = args.module
    if mod in CLI_AI_FLOW:
        CLI_AI_FLOW[mod](ctx)
        return
    if mod in CLI_DISPATCHERS:
        target = (args.target or [""])[0]
        if mod == "breach":
            mode = (args.target or ["", "email"])[1] if len(args.target or []) > 1 else "email"
            CLI_DISPATCHERS[mod](ctx, target, mode=mode)
        elif mod == "social":
            platform = (args.target or ["", "github"])[1] if len(args.target or []) > 1 else "github"
            CLI_DISPATCHERS[mod](ctx, target, platform=platform)
        else:
            CLI_DISPATCHERS[mod](ctx, target)
        return
    err(f"Unknown CLI module: {mod}. Valid: {','.join(list(CLI_DISPATCHERS.keys()) + list(CLI_AI_FLOW.keys()))}")
    sys.exit(2)


def main():
    parser = argparse.ArgumentParser(prog="almighty-osint-ai", description="AI-powered OSINT toolkit")
    parser.add_argument("-m", "--module", help="Run a single module non-interactively (username|email|domain|ip|phone|breach|image|crypto|social|auto)")
    parser.add_argument("-t", "--target", action="append", help="Target value(s) for the module (repeat: 1st=target, 2nd=mode/platform)")
    parser.add_argument("--persona", help="Override persona for this run (analyst|investigator|redteam|journalist|soc|linkanalyst|stylometrist|translator|geolocator)")
    parser.add_argument("--config", default=str(CONFIG_PATH), help="Config file path")
    args = parser.parse_args()

    cfg = Config(args.config)
    if args.persona:
        if args.persona.lower() in personas.PERSONAS:
            cfg.set("ai.persona", args.persona.lower())
        else:
            err(f"Unknown persona: {args.persona}")
            sys.exit(2)
    ctx = AppCtx(cfg)

    if args.module:
        cli_run(ctx, args)
        return

    try:
        main_menu(ctx)
    except (KeyboardInterrupt, EOFError):
        pass
    print(f"\n  {C.DIM}Goodbye.{C.RESET}\n")


if __name__ == "__main__":
    main()
