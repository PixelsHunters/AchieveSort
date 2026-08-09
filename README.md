# AchieveSort

> Calcula qué juegos de tu biblioteca de Steam te conviene rematar primero, ordenando tus logros pendientes por rareza global.

Calcula el **MDO** (dificultad media de tus logros pendientes) de toda tu biblioteca de Steam, para saber qué juegos te conviene rematar primero (fáciles) y cuáles son el reto de verdad (raros).

Ver [CHANGELOG.md](CHANGELOG.md) para el historial de versiones.

## Qué hace

1. Lee tu biblioteca de juegos de Steam.
2. Para cada juego, compara tus logros desbloqueados con el % global de jugadores que tiene cada logro.
3. Calcula un **MDO** por juego: la media de "rareza" de tus logros pendientes.
   - **MDO bajo** → lo que te falta es común, fácil de rematar.
   - **MDO alto** → lo que te falta es raro/costoso.
4. Te muestra una tabla ordenada de más fácil a más difícil, y la exporta también a CSV.

## Funciones adicionales

- **Filtro por horas jugadas**: al ejecutarlo, puedes excluir juegos con pocas horas para centrarte en los que de verdad juegas.
- **Caché local** (`achievesort_cache.json`): los porcentajes globales de logros apenas cambian, así que se guardan localmente 7 días. Las siguientes ejecuciones son más rápidas porque no repiten esas llamadas a la API (sí se sigue consultando siempre tu progreso personal, que es lo que puede cambiar entre ejecuciones).
- **Exportación a CSV**: cada ejecución genera `achievesort_resultados_AAAAMMDD_HHMMSS.csv` junto al ejecutable, con todos los datos de la tabla.

## Privacidad

Tu API key y tu SteamID64 se piden por consola en cada ejecución y solo existen en memoria mientras el programa corre; no se guardan en ningún archivo. La única información que se persiste en disco es la caché de porcentajes globales de logros (públicos, no personales) y los CSV de resultados que tú mismo generas.

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
