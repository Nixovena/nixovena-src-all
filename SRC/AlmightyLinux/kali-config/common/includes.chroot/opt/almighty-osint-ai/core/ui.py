import os
import sys
import time
import threading


class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    RED     = "\033[31m"
    GREEN   = "\033[32m"
    YELLOW  = "\033[33m"
    BLUE    = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN    = "\033[36m"
    WHITE   = "\033[37m"
    BR_RED  = "\033[91m"
    BR_GRN  = "\033[92m"
    BR_YEL  = "\033[93m"
    BR_BLU  = "\033[94m"
    BR_MAG  = "\033[95m"
    BR_CYN  = "\033[96m"


def clear():
    os.system("clear" if os.name != "nt" else "cls")


def banner():
    art = (
        f"{C.BR_MAG}{C.BOLD}"
        " █████╗ ██╗     ███╗   ███╗██╗ ██████╗ ██╗  ██╗████████╗██╗   ██╗\n"
        "██╔══██╗██║     ████╗ ████║██║██╔════╝ ██║  ██║╚══██╔══╝╚██╗ ██╔╝\n"
        "███████║██║     ██╔████╔██║██║██║  ███╗███████║   ██║    ╚████╔╝ \n"
        "██╔══██║██║     ██║╚██╔╝██║██║██║   ██║██╔══██║   ██║     ╚██╔╝  \n"
        "██║  ██║███████╗██║ ╚═╝ ██║██║╚██████╔╝██║  ██║   ██║      ██║   \n"
        "╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝      ╚═╝   \n"
        f"{C.RESET}{C.DIM}  AI-Powered OSINT Toolkit  |  Ollama / Local / API  |  Almighty Linux{C.RESET}\n"
    )
    print(art)


def box(title, color=C.CYAN):
    line = "═" * (len(title) + 4)
    print(f"\n{color}{C.BOLD}╔{line}╗{C.RESET}")
    print(f"{color}{C.BOLD}║  {title}  ║{C.RESET}")
    print(f"{color}{C.BOLD}╚{line}╝{C.RESET}\n")


def row(label, value, label_color=C.CYAN, value_color=C.WHITE):
    print(f"  {label_color}{label:<26}{C.RESET}  {value_color}{value}{C.RESET}")


def ok(msg):    print(f"  {C.GREEN}[OK]{C.RESET}    {msg}")
def warn(msg):  print(f"  {C.YELLOW}[WARN]{C.RESET}  {msg}")
def err(msg):   print(f"  {C.RED}[ERR]{C.RESET}   {msg}")
def info(msg):  print(f"  {C.BLUE}[INFO]{C.RESET}  {msg}")
def dim(msg):   print(f"  {C.DIM}{msg}{C.RESET}")


def prompt(text, default=None):
    suffix = f" {C.DIM}[{default}]{C.RESET}" if default else ""
    raw = input(f"  {C.YELLOW}> {C.RESET}{text}{suffix}: ").strip()
    return raw or (default or "")


def pause():
    input(f"\n  {C.DIM}Press Enter to continue...{C.RESET}")


class _Spinner:
    def __init__(self, text):
        self.text = text
        self.stop = False
        self.thread = None

    def _run(self):
        chars = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
        i = 0
        while not self.stop:
            sys.stdout.write(f"\r  {C.CYAN}{chars[i % len(chars)]}{C.RESET}  {self.text}")
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        sys.stdout.write("\r" + " " * (len(self.text) + 8) + "\r")
        sys.stdout.flush()

    def start(self):
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return self

    def end(self):
        self.stop = True
        if self.thread:
            self.thread.join(timeout=0.5)


def spinner(text):
    return _Spinner(text).start()
