# Changelog

Todos los cambios notables de este proyecto se documentan en este archivo.

El formato sigue [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/),
y este proyecto usa [Versionado Semántico](https://semver.org/lang/es/).

## [1.1.0] - 2026-08-09

### Añadido
- **Caché local de logros** (`achievesort_cache.json`): los porcentajes globales de cada logro se guardan en disco durante 7 días, evitando repetir esas llamadas a la API en próximas ejecuciones. Acelera notablemente las ejecuciones posteriores a la primera.
- **Filtro por horas jugadas**: al arrancar, se puede excluir juegos con pocas horas jugadas para centrar el análisis solo en los que de verdad se juegan.
- **Exportación a CSV**: cada ejecución genera automáticamente `achievesort_resultados_AAAAMMDD_HHMMSS.csv` junto al ejecutable, con juego, AppID, MDO, logros pendientes/totales y horas jugadas.
- Columna de **horas jugadas** añadida también a la tabla que se muestra en consola.
- Aviso al final de la ejecución indicando cuántos juegos se consultaron a la API frente a cuántos vinieron de la caché.

### Cambiado
- `.gitignore` actualizado para excluir la caché (`achievesort_cache.json`) y los CSV generados (`achievesort_resultados_*.csv`), para que no se suban al repositorio por error.

## [1.0.0] - 2026-08-08

### Añadido
- Cálculo del **MDO** (dificultad media de logros pendientes) para toda la biblioteca de Steam del usuario, usando `GetOwnedGames`, `GetPlayerAchievements` y `GetGlobalAchievementPercentagesForApp`.
- Introducción de API key y SteamID64 por consola en cada ejecución, sin persistencia de credenciales.
- Validaciones de formato de API key (32 caracteres) y SteamID64 (17 dígitos).
- Verificación de credenciales antes de analizar la biblioteca completa.
- Diagnóstico detallado cuando no se encuentran juegos con logros pendientes (perfil privado, juego ya al 100%, datos globales no disponibles, etc.).
- Manejo de errores aislado por juego, para que un fallo puntual no interrumpa el análisis completo.
- Pausa final (`Pulsa Enter para salir...`) para que la ventana del `.exe` no se cierre antes de poder leer el resultado.
- Icono propio para el ejecutable compilado con PyInstaller.
- Primer release público en GitHub con `.exe` compilado.
