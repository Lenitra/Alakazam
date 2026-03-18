# ALCASAR Auto-Connect

Surveille la connexion internet et se reconnecte automatiquement au portail captif ALCASAR en cas de perte.

## Fonctionnement

1. Ping TCP parallele sur `8.8.8.8`, `1.1.1.1`, `208.67.222.222` a intervalle regulier
2. Si aucun hote ne repond, soumission automatique du formulaire de connexion ALCASAR via `urllib`
3. La surveillance reprend

## Prerequis

- Python 3.14+

## Installation

```bash
pip install python-dotenv
```

## Configuration

Creer un fichier `.env` a la racine :

```
ALCASAR_USER=identifiant
ALCASAR_PASS=motdepasse
PING_INTERVAL=5
PORTAL_URL=http://alcasar.lan/intercept.php
```

| Variable | Description | Defaut |
|---|---|---|
| `ALCASAR_USER` | Identifiant ALCASAR | — |
| `ALCASAR_PASS` | Mot de passe ALCASAR | — |
| `PING_INTERVAL` | Intervalle entre chaque test (secondes) | `5` |
| `PORTAL_URL` | URL du portail captif | `http://alcasar.lan/intercept.php` |

## Lancement

```bash
python main.py
```

Ou double-cliquer sur `start.bat`.
