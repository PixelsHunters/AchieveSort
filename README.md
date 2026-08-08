# AchieveSort

> Calcula qué juegos de tu biblioteca de Steam te conviene rematar primero, ordenando tus logros pendientes por rareza global.

Calcula el **MDO** (dificultad media de tus logros pendientes) de toda tu biblioteca de Steam, para saber qué juegos te conviene rematar primero (fáciles) y cuáles son el reto de verdad (raros).

## Qué hace

1. Lee tu biblioteca de juegos de Steam.
2. Para cada juego, compara tus logros desbloqueados con el % global de jugadores que tiene cada logro.
3. Calcula un **MDO** por juego: la media de "rareza" de tus logros pendientes.
   - **MDO bajo** → lo que te falta es común, fácil de rematar.
   - **MDO alto** → lo que te falta es raro/costoso.
4. Te muestra una tabla ordenada de más fácil a más difícil.

## Privacidad

No se guarda ningún dato. Tu API key y tu SteamID64 se piden por consola en cada ejecución y solo existen en memoria mientras el programa corre.

## Requisitos

Para tu perfil de Steam, la opción **"Detalles del juego"** en la configuración de privacidad debe estar en **Público**; si no, la API no te devuelve tus logros.

Necesitas también:
- Una API key de Steam: https://steamcommunity.com/dev/apikey
- Tu SteamID64: https://steamid.io

## Uso

### Opción A: ejecutable (Windows, sin instalar nada)

Descarga `AchieveSort.exe` desde [Releases](../../releases) y ejecútalo.

### Opción B: desde código fuente

```bash
pip install -r requirements.txt
python achievesort.py
```

## Compilar tu propio ejecutable

```bash
pip install pyinstaller
python -m PyInstaller --onefile --console --name AchieveSort --icon icon.ico achievesort.py
```

El `.exe` resultante queda en `dist/AchieveSort.exe`.

## Licencia

MIT
