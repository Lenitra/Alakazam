import os
import socket
import ssl
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from html.parser import HTMLParser

from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
USERNAME = os.getenv("ALCASAR_USER")
PASSWORD = os.getenv("ALCASAR_PASS")
PORTAL_URL = os.getenv("PORTAL_URL", "http://alcasar.lan/intercept.php")

PING_TARGETS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
PING_INTERVAL = int(os.getenv("PING_INTERVAL", 5))
BAR_WIDTH = 30

# --- Couleurs ANSI ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"
BG_GREEN = "\033[42m"
BG_RED = "\033[41m"
BLACK = "\033[30m"

# --- Etat global ---
connected = True
reconnections = 0
last_reconnection = None
current_progress = 0
logs = []

# SSL context pour accepter les certificats auto-signes (courant sur ALCASAR)
_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


# --- Parseur de formulaire HTML ---
class _FormParser(HTMLParser):
    """Extrait l'action et les champs du premier <form> trouve."""

    def __init__(self):
        super().__init__()
        self.action = ""
        self.method = "GET"
        self.inputs = []  # [(name, value, type), ...]
        self._in_form = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "form":
            self._in_form = True
            self.action = a.get("action", "")
            self.method = a.get("method", "GET").upper()
        elif tag == "input" and self._in_form:
            name = a.get("name", "")
            if name:
                self.inputs.append((name, a.get("value", ""), a.get("type", "text").lower()))

    def handle_endtag(self, tag):
        if tag == "form":
            self._in_form = False


def add_log(level, message, refresh=False):
    now = datetime.now().strftime("%H:%M:%S")
    icons = {
        "ok":   f"{GREEN}[+]{RESET}",
        "fail": f"{RED}[X]{RESET}",
        "warn": f"{YELLOW}[!]{RESET}",
        "step": f"{MAGENTA}[>]{RESET}",
        "ping": f"{CYAN}[~]{RESET}",
    }
    icon = icons.get(level, "[?]")
    logs.append(f"  {DIM}{now}{RESET}  {icon} {message}")
    if len(logs) > 10:
        logs.pop(0)
    if refresh:
        render(current_progress)


def ping_host(ip, port=53, timeout=1):
    """Test de connectivite via socket TCP (port 53 = DNS)."""
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((ip, port))
        sock.close()
        ms = round((time.time() - start) * 1000)
        return ip, True, ms
    except (socket.timeout, OSError):
        ms = round((time.time() - start) * 1000)
        return ip, False, ms


def check_connection():
    """Teste tous les hotes en parallele — retourne True des qu'un seul repond."""
    with ThreadPoolExecutor(max_workers=len(PING_TARGETS)) as pool:
        results = list(pool.map(ping_host, PING_TARGETS))

    for ip, ok, ms in results:
        if ok:
            add_log("ok", f"{GREEN}{ip} OK {DIM}{ms}ms{RESET}", refresh=True)
            return True

    fastest = min(results, key=lambda r: r[2])
    add_log("fail", f"{RED}Tous timeout (meilleur: {fastest[0]} {DIM}{fastest[2]}ms){RESET}", refresh=True)
    return False


def progress_bar(elapsed, total):
    ratio = min(elapsed / total, 1.0)
    filled = int(BAR_WIDTH * ratio)
    empty = BAR_WIDTH - filled
    bar = f"{CYAN}{'█' * filled}{DIM}{'░' * empty}{RESET}"
    pct = int(ratio * 100)
    return f"  {bar}  {BOLD}{pct}%{RESET}  ({elapsed:.0f}s / {total}s)"


def render(elapsed):
    os.system("cls")

    # Banniere
    print(f"""
  {CYAN}{BOLD}╔══════════════════════════════════════════╗
  ║         ALCASAR AUTO-CONNECT             ║
  ╚══════════════════════════════════════════╝{RESET}
""")

    # Status
    if connected:
        status = f"  {BG_GREEN}{BLACK}{BOLD}  CONNECTE  {RESET}"
    else:
        status = f"  {BG_RED}{WHITE}{BOLD}  DECONNECTE  {RESET}"
    print(f"  {DIM}Status :{RESET}  {status}")
    print()

    # Infos
    print(f"  {DIM}Utilisateur   :{RESET}  {BOLD}{USERNAME}{RESET}")
    print(f"  {DIM}Intervalle    :{RESET}  {BOLD}{PING_INTERVAL}s{RESET}")
    print(f"  {DIM}Reconnexions  :{RESET}  {BOLD}{reconnections}{RESET}")
    if last_reconnection:
        print(f"  {DIM}Derniere reco :{RESET}  {BOLD}{last_reconnection}{RESET}")
    print()

    # Barre de progression
    print(f"  {DIM}Prochain ping :{RESET}")
    print(progress_bar(elapsed, PING_INTERVAL))
    print()

    # Separateur
    print(f"  {DIM}{'─' * 42}{RESET}")
    print(f"  {DIM}Journal{RESET}")
    print(f"  {DIM}{'─' * 42}{RESET}")

    # Logs
    for entry in logs:
        print(entry)
    if not logs:
        print(f"  {DIM}En attente...{RESET}")
    print()


def login_alcasar():
    global connected, reconnections, last_reconnection

    add_log("warn", f"{YELLOW}Aucun hote joignable{RESET}", refresh=True)
    connected = False
    add_log("warn", f"{YELLOW}Reconnexion ALCASAR...{RESET}", refresh=True)

    try:
        # 1. Charger la page du portail
        add_log("step", "Chargement du portail", refresh=True)
        req = urllib.request.Request(PORTAL_URL)
        resp = urllib.request.urlopen(req, timeout=10, context=_ssl_ctx)
        html = resp.read().decode("utf-8", errors="replace")
        base_url = resp.url  # URL finale apres redirection eventuelle

        # 2. Parser le formulaire
        parser = _FormParser()
        parser.feed(html)

        if not parser.inputs:
            add_log("fail", f"{RED}Aucun formulaire trouve sur le portail{RESET}", refresh=True)
            return

        # 3. Remplir les champs : password par type, username = premier champ texte
        fields = {}
        username_filled = False
        for name, value, input_type in parser.inputs:
            if input_type == "password":
                fields[name] = PASSWORD
            elif input_type in ("text", "email") and not username_filled:
                fields[name] = USERNAME
                username_filled = True
            else:
                fields[name] = value  # champs hidden, submit, etc.

        # 4. Determiner l'URL d'action
        action = parser.action
        if action and not action.startswith("http"):
            action = urllib.parse.urljoin(base_url, action)
        elif not action:
            action = base_url

        # 5. Soumettre le formulaire
        add_log("step", f"Envoi des identifiants vers {action}", refresh=True)
        data = urllib.parse.urlencode(fields).encode("utf-8")
        post_req = urllib.request.Request(action, data=data, method="POST")
        urllib.request.urlopen(post_req, timeout=10, context=_ssl_ctx)

        reconnections += 1
        last_reconnection = datetime.now().strftime("%H:%M:%S")
        connected = True
        add_log("ok", f"{GREEN}{BOLD}Reconnexion reussie !{RESET}", refresh=True)

    except Exception as e:
        add_log("fail", f"{RED}Echec : {e}{RESET}", refresh=True)


def main():
    global connected, current_progress

    os.system("")  # active les codes ANSI sur Windows
    add_log("ok", f"{GREEN}Demarrage de la surveillance{RESET}")

    while True:
        # Phase ping
        current_progress = 0
        connected = check_connection()

        if not connected:
            login_alcasar()

        # Compte a rebours avec barre de progression
        for tick in range(PING_INTERVAL):
            current_progress = tick
            render(tick)
            time.sleep(1)
        current_progress = PING_INTERVAL
        render(PING_INTERVAL)


if __name__ == "__main__":
    main()
