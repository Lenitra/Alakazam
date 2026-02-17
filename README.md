# ALCASAR Auto-Connect

Script de surveillance de connexion internet qui se reconnecte automatiquement au portail captif ALCASAR en cas de perte de connexion.

## Fonctionnement

1. Un ping est envoy sur une IP fiable choisie au hasard (`8.8.8.8`, `1.1.1.1`, `208.67.222.222`) a intervalle regulier
2. Si le ping echoue, le script lance Firefox en mode headless et se connecte automatiquement au portail ALCASAR
3. Une fois reconnecte, la surveillance reprend

## Prerequis

- Python 3
- Firefox
- geckodriver

## Installation

```bash
pip install python-dotenv selenium
```

## Configuration

Creer un fichier `.env` a la racine du projet :

```
ALCASAR_USER=identifiant
ALCASAR_PASS=motdepasse
PING_INTERVAL=5
```

| Variable | Description |
|---|---|
| `ALCASAR_USER` | Identifiant du portail ALCASAR |
| `ALCASAR_PASS` | Mot de passe du portail ALCASAR |
| `PING_INTERVAL` | Intervalle entre chaque test de connexion (en secondes) |

## Lancement

Double-cliquer sur `start.bat` ou :

```bash
python main.py
```

## Interface console

```
  ╔══════════════════════════════════════════╗
  ║         ALCASAR AUTO-CONNECT             ║
  ╚══════════════════════════════════════════╝

  Status :    CONNECTE

  Utilisateur   :  t.lemartinel
  Intervalle    :  5s
  Reconnexions  :  0

  Prochain ping :
  ██████████████████░░░░░░░░░░░░  60%  (3s / 5s)

  ──────────────────────────────────────────
  Journal
  ──────────────────────────────────────────
  14:32:03  [+] 8.8.8.8 OK 12ms
  14:32:08  [+] 1.1.1.1 OK 15ms
```
