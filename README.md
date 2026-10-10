# Inventory

Application web d’inventaire personnel sur le réseau local. Interface mobile en français, API REST FastAPI, base SQLite et photos JPEG compressées sur disque.

## Installation sur Ubuntu

Depuis le dépôt cloné, exécutez :

```bash
./scripts/install.sh
```

Le script copie l’application dans `~/.local/share/inventory/`, crée un environnement Python isolé, installe les dépendances et active un service utilisateur `systemd`. L’application reste disponible en HTTP sur le port `18765`. Pour la dictée, elle propose aussi HTTPS sur le port `18766`; le port `18767` sert uniquement à télécharger le certificat local. Le script active aussi `linger` pour démarrer le service avant la connexion utilisateur quand les droits le permettent. Si `linger` échoue, exécutez la commande indiquée par le script avec `sudo`.

### Activer la dictée sur les appareils

Les navigateurs limitent l’accès au micro sur une adresse HTTP du réseau local. L’application génère donc une petite autorité de certification locale. Sur le téléphone, connecté au même Wi-Fi, ouvrez `http://IP_DU_PC:18767/ca.crt`, puis installez et approuvez le certificat « Inventory Local Certificate Authority » dans les réglages de certificats de l’appareil. Ensuite ouvrez `https://IP_DU_PC:18766` et autorisez l’accès au micro.

Sur Android, l’installation du certificat se trouve généralement dans **Paramètres → Sécurité → Chiffrement et identifiants → Installer un certificat**. Sur iPhone, ouvrez le profil téléchargé dans **Réglages**, installez-le, puis activez sa confiance dans **Réglages → Général → Informations → Réglages de confiance des certificats**. Les intitulés peuvent varier selon la version du système.

Le certificat racine est conservé dans `~/.inventory/tls/ca.crt`; sa clé privée ne doit pas être partagée. Si l’adresse IP du PC change, relancez `./scripts/setup-tls.sh` depuis le répertoire d’installation, puis redémarrez le service.

## Commandes utiles

```bash
systemctl --user status inventory.service
systemctl --user restart inventory.service
journalctl --user -u inventory.service -f
```

Les données sont conservées dans `~/.inventory/` : SQLite, photos, certificat local et archives ZIP.

## Développement local

Python 3.10 ou supérieur est recommandé.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 18765 --reload
```

## API

En mode installé, la documentation interactive de l’API est disponible sur `http://IP_DU_PC:18765/docs` ou `https://IP_DU_PC:18766/docs`. Les routes principales sont `GET /api/items?q=...` (50 résultats maximum par réponse), `GET/PUT/DELETE /api/items/{id}`, `POST /api/items`, `GET /api/export` et `POST /api/import`.

## Sauvegarde

Le bouton **Exporter ZIP** télécharge une archive autonome contenant la base SQLite, le manifeste de données et les photos. **Restaurer un ZIP** demande confirmation et remplace tout l’inventaire actif. Les archives utilisent un manifeste versionné (`format_version: 1`).

## Limites actuelles

- Accès local sans authentification, comme prévu pour le réseau Wi-Fi de confiance.
- Les photos JPEG, PNG et WebP sont converties en JPEG, redimensionnées à 1600 px maximum et compressées autour de 200 ko.
- La dictée utilise la reconnaissance vocale du navigateur et dépend de sa prise en charge et de sa connexion au service vocal du navigateur.
- La liste et la recherche renvoient au maximum 50 objets par réponse; la recherche permet d’affiner au-delà.
- La prise de photo utilise la caméra en direct et n’ouvre pas le sélecteur de fichiers. La version courante est affichée en bas de page; les réponses désactivent le cache et une page ouverte recharge automatiquement lorsqu’une nouvelle version est déployée. Elle nécessite HTTPS et une autorisation caméra.
