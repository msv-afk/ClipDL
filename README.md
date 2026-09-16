# ClipDL : YouTube / Twitch / TikTok → MP4 / MP3 (en local)

Interface web qui tourne **uniquement sur ton PC** (http://127.0.0.1), sans compte ni clé API.
Moteur : [yt-dlp](https://github.com/yt-dlp/yt-dlp) (téléchargement) + FFmpeg (conversion).

**Compatibilité :** Windows 10 et 11 en 64 bits (Python 3.13 ne prend plus en charge Windows 7 ni 8).

## Télécharger l'exe directement

Onglet **Releases** du dépôt → `ClipDL.exe` (compilé automatiquement par GitHub Actions).

## 1. Prérequis (une seule fois)

| Commande (PowerShell) | À quoi ça sert |
|---|---|
| `py --version` | Vérifie que Python est installé. Il faut la version 3.10 ou plus récente (tu as la 3.13). |
| `ffmpeg -version` | Vérifie que FFmpeg est dans le PATH. Si ce n'est pas le cas, l'appli utilise la copie de FFmpeg fournie par `imageio-ffmpeg`. |
| `winget install DenoLand.Deno` | **Recommandé pour YouTube.** `winget` est le gestionnaire de paquets de Windows et installe ici Deno, un moteur JavaScript. Depuis fin 2025, yt-dlp en a besoin pour résoudre les protections de YouTube. Sans Deno, certaines vidéos ou qualités peuvent échouer. Redémarre ensuite le terminal pour que le PATH soit mis à jour. |

## 2. Tester sans compiler

Double-clique sur **`run.bat`**. Au premier lancement, le script :
1. `py -3 -m venv .venv` crée un **environnement virtuel**, c'est-à-dire un dossier Python isolé. Les paquets y sont installés sans toucher à ton Python système.
2. `call .venv\Scripts\activate.bat` active cet environnement : les commandes `python` et `pip` suivantes utilisent alors le dossier `.venv`.
3. `python -m pip install -r requirements.txt` installe les paquets listés dans `requirements.txt` (Flask, yt-dlp, imageio-ffmpeg, PyInstaller).
4. `python app.py` lance le serveur, puis ton navigateur s'ouvre tout seul.

## 3. Créer le .exe

Double-clique sur **`build.bat`**. Le script fait les étapes ci-dessus, puis lance :

```
pyinstaller --noconfirm --onefile --name ClipDL --add-data "templates;templates" --collect-all yt_dlp --collect-all yt_dlp_ejs --collect-data imageio_ffmpeg app.py
```

- `--onefile` regroupe tout dans **un seul** `.exe` (Python compris).
- `--name ClipDL` donne son nom au fichier : `ClipDL.exe`.
- `--add-data "templates;templates"` intègre la page HTML (format `source;destination`, avec un `;` sous Windows).
- `--collect-all yt_dlp` / `yt_dlp_ejs` embarque tous les modules de yt-dlp, dont une partie est chargée dynamiquement et échapperait sinon à PyInstaller.
- `--collect-data imageio_ffmpeg` embarque la copie de secours de FFmpeg.
- `--noconfirm` écrase l'ancien build sans poser de question.

Résultat : **`dist\ClipDL.exe`**. Tu peux le copier où tu veux. Double-clique dessus : une console s'ouvre (le serveur), puis la page s'affiche. **Ferme la console pour quitter l'appli.**

> Au premier lancement, Windows SmartScreen peut afficher « Windows a protégé votre ordinateur », car l'exe n'est pas signé. Clique sur *Informations complémentaires*, puis sur *Exécuter quand même*.

## 4. Utilisation

- Colle un lien. Si le presse-papiers contient déjà un lien compatible, il est collé automatiquement.
- Choisis **MP4** (qualité max : 480p à 4K) ou **MP3** (128, 192 ou 320 kbps), puis clique sur **Convertir**.
- Les fichiers sont enregistrés dans `Téléchargements\ClipDL`. Le bouton « Télécharger » en propose aussi une copie via le navigateur.
- Formats pris en charge : vidéos YouTube et Shorts, VOD et clips Twitch, vidéos TikTok. Les **lives en cours** sont refusés, car le téléchargement ne se terminerait jamais.
- Les MP4 sont convertis en priorité en H.264 + AAC, pour être lisibles partout.

## 5. Quand YouTube « casse »

YouTube modifie souvent son site. Si les téléchargements échouent, **relance `build.bat`** : il met yt-dlp à jour (`pip install --upgrade`) et recompile l'exe. La version de yt-dlp est indiquée en bas de la page.

## Rappel

Réserve cet outil à un usage personnel, pour du contenu que tu as le droit de télécharger. Les conditions d'utilisation de YouTube et TikTok interdisent en principe le téléchargement hors de leurs propres outils.
