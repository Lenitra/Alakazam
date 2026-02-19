import os
import socket
import time
import atexit
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

# --- Configuration ---
USERNAME = os.getenv("ALCASAR_USER")
PASSWORD = os.getenv("ALCASAR_PASS")

XPATH_ID = "/html/body/div/div[1]/div/div[2]/form/div[3]/div[2]/div[1]/div[2]/input"
XPATH_MDP = "/html/body/div/div[1]/div/div[2]/form/div[3]/div[2]/div[2]/div[2]/input"
XPATH_BTN = "/html/body/div/div[1]/div/div[2]/form/div[4]/div/input"

PING_TARGETS = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
PING_INTERVAL = int(os.getenv("PING_INTERVAL", 5))
WAIT_TIMEOUT = int(os.getenv("WAIT_TIMEOUT", 8))
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

# WebDriver persistant (créé à la première reconnexion)
driver = None


def _cleanup_driver():
    global driver
    try:
        if driver:
            driver.quit()
    except Exception:
        pass


atexit.register(_cleanup_driver)


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
    """Test de connectivite via socket TCP (port 53 = DNS) — bien plus rapide qu'un subprocess ping."""
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

    global driver
    # Création du driver à la première utilisation et réutilisation ensuite
    if driver is None:
        options = webdriver.FirefoxOptions()
        options.add_argument("--headless")
        add_log("step", "Ouverture de Firefox (persistant)", refresh=True)
        driver = webdriver.Firefox(options=options)
        # réduire les temps d'attente généraux
        try:
            driver.set_page_load_timeout(15)
        except Exception:
            pass

    try:
        add_log("step", "Chargement du portail", refresh=True)
        driver.get("http://alcasar.lan/intercept.php")

        wait = WebDriverWait(driver, WAIT_TIMEOUT)

        add_log("step", "Saisie de l'identifiant", refresh=True)
        champ_id = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_ID)))
        champ_id.clear()
        champ_id.send_keys(USERNAME)

        add_log("step", "Saisie du mot de passe", refresh=True)
        champ_mdp = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_MDP)))
        champ_mdp.clear()
        champ_mdp.send_keys(PASSWORD)

        add_log("step", "Clic sur Connexion", refresh=True)
        bouton = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_BTN)))
        bouton.click()

        # Attendre que l'URL change (indique souvent que la connexion a réussie)
        try:
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                lambda d: "intercept.php" not in d.current_url
            )
        except Exception:
            # fallback: courte pause minimale
            time.sleep(1)

        reconnections += 1
        last_reconnection = datetime.now().strftime("%H:%M:%S")
        connected = True
        add_log("ok", f"{GREEN}{BOLD}Reconnexion reussie !{RESET}", refresh=True)
    except Exception as e:
        add_log("fail", f"{RED}Echec : {e}{RESET}", refresh=True)
        # Si le driver est dans un état instable, le fermer pour recréation
        try:
            driver.quit()
        except Exception:
            pass
        driver = None


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
