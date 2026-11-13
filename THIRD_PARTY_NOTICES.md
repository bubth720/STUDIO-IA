# Dépendances, licences et sources

Le code STUDIO IA est MIT. Les composants suivants conservent leurs licences.
L'archive est expérimentale, sans modification des bibliothèques tierces.

| Composant | Version / licence | Distribution |
|---|---|---|
| CPython | version dans BUILD_INFO.json ; PSF-2.0 et mentions incluses | runtime embarqué par PyInstaller |
| PySide6-Essentials / Shiboken6 | 6.8.3 ; choix LGPL-3.0, autres licences possibles upstream | bibliothèques dynamiques et binding dans `_internal` |
| Qt | 6.8.3 ; LGPL-3.0 et licences tierces QtBase/QtSvg/QtWayland | bibliothèques et plugins détectés par PyInstaller |
| ICU | 73.2 dans le wheel Linux ; licences Unicode/ICU | bibliothèques de données/internationalisation et notice spécifique |
| Bibliothèques système Linux | versions d'origine et licences dans BINARY_LICENSES.json | notices exactes dpkg, textes communs et URL des sources correspondantes inclus |
| PyInstaller | 6.13.0 ; GPL-2.0 avec exception bootloader | outil de build, exception autorise distribution de l'application |
| FFmpeg / ffprobe | version et configuration réelles dans doctor | **non inclus** ; licence de la compilation choisie par l'utilisateur |
| Video2X / poids neuronaux | non installés et non qualifiés | **non inclus** |

Sources correspondantes et notices officielles :

- QtBase 6.8.3 : https://download.qt.io/archive/qt/6.8/6.8.3/submodules/qtbase-everywhere-src-6.8.3.tar.xz
- QtWayland 6.8.3 (plugins de plateforme, selon OS) : https://download.qt.io/archive/qt/6.8/6.8.3/submodules/qtwayland-everywhere-src-6.8.3.tar.xz
- QtSvg 6.8.3 : https://download.qt.io/archive/qt/6.8/6.8.3/submodules/qtsvg-everywhere-src-6.8.3.tar.xz
- ICU 73.2 : https://github.com/unicode-org/icu/releases/tag/release-73-2
- PySide/Shiboken 6.8.3 : https://download.qt.io/official_releases/QtForPython/pyside6/PySide6-6.8.3-src/
- Dépôts sources : https://code.qt.io/cgit/pyside/pyside-setup.git/tag/?h=v6.8.3 et https://code.qt.io/cgit/qt/qtbase.git/tag/?h=v6.8.3
- Python : https://www.python.org/downloads/source/ et https://docs.python.org/3/license.html
- PyInstaller : https://github.com/pyinstaller/pyinstaller/tree/v6.13.0 et https://pyinstaller.org/en/v6.13.0/license.html
- FFmpeg : https://ffmpeg.org/legal.html ; les compilations libx264 sont généralement GPL.

Les textes LGPL/GPL et notices QtBase/QtSvg/QtWayland/ICU se trouvent dans `licenses/`. Aucune
modification de Qt/PySide/Python n'est apportée. Le mode dossier conserve les
bibliothèques partagées : l'utilisateur peut les remplacer par des versions
compatibles et reconstruire depuis les sources MIT et les commandes versionnées.
Aucune restriction additionnelle sur le débogage de ces remplacements.
Ne pas convertir en binaire monolithique verrouillé sans réexaminer les obligations.

Les dépendances de développement (pytest MIT, Ruff MIT, mypy MIT, pip-audit
Apache-2.0) ne sont pas nécessaires à l'utilisation. Leurs versions et les
vulnérabilités connues sont consignées au rapport de build. Les bibliothèques
système externes suivent les notices de l'OS ; les copies incluses dans le ZIP Linux
ont leurs copyrights et versions source dans `BINARY_LICENSES.json`. Les archives
source exactes sont accessibles via les liens Debian Snapshot ou Ubuntu Launchpad
du même inventaire. Les fichiers distribués sont aussi inventoriés
par empreinte dans `FILES_SHA256.json`. Cet inventaire n'est pas une expertise
juridique ni une garantie d'absence de vulnérabilités, notamment dans Qt/FFmpeg.
