"""
achievesort.py

AchieveSort — Calcula el MDO (Mean Difficulty of Outstanding achievements) de tus juegos
pendientes en Steam: para cada juego con logros sin desbloquear, mide qué tan
"raros" son esos logros pendientes usando el % global de jugadores que los
tienen.

MDO bajo  -> lo que te falta es "fácil" (mucha gente lo tiene ya)
MDO alto  -> lo que te falta es raro/costoso

Requisitos:
    pip install requests

Configuración:
    Al ejecutar el script, te pedirá tu API key y tu SteamID64 por consola.
    No se guardan en ningún archivo ni variable de entorno: solo existen en
    memoria mientras el programa corre, y se pierden al cerrarlo. Cada vez
    que lo ejecutes tendrás que volver a introducirlos.

    1. Consigue tu API key en https://steamcommunity.com/dev/apikey
    2. Consigue tu SteamID64 (steamid.io o tu perfil de Steam)

Funciones adicionales:
    - Caché local de porcentajes globales de logros (achievements_cache.json),
      para no repetir esa llamada a la API en próximas ejecuciones.
    - Filtro opcional por horas jugadas mínimas.
    - Exportación de resultados a CSV.
"""

import csv
import json
import os
import sys
import time
from datetime import datetime, timedelta

import requests

BASE_URL = "https://api.steampowered.com"

# La caché se guarda junto al ejecutable/script, no en la carpeta desde la
# que se lanza, para que siempre sea la misma independientemente de dónde
# se ejecute.
if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

CACHE_PATH = os.path.join(APP_DIR, "achievesort_cache.json")
CACHE_MAX_AGE_DAYS = 7  # los % globales apenas varían; una semana es un buen margen


def pedir_credenciales():
    """Pide API key y SteamID64 por consola. No los persiste en ningún sitio."""
    print("=== AchieveSort ===")
    print("Estos datos no se guardan; se piden en cada ejecución.\n")

    api_key = input("Introduce tu API key de Steam: ").strip()
    steam_id = input("Introduce tu SteamID64 (17 dígitos): ").strip()

    if not api_key:
        raise SystemExit("No se ha introducido una API key. Cancelando.")
    if len(api_key) != 32:
        raise SystemExit(
            f"La API key debe tener 32 caracteres y tiene {len(api_key)}. "
            "Revisa que no se haya pegado dos veces o con espacios. Cancelando."
        )
    if not steam_id.isdigit() or len(steam_id) != 17:
        raise SystemExit("El SteamID64 debe ser un número de 17 dígitos. Cancelando.")

    return api_key, steam_id


def cargar_cache():
    """Carga la caché de % globales desde disco. Devuelve un dict vacío si no existe o está corrupta."""
    if not os.path.exists(CACHE_PATH):
        return {}
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def guardar_cache(cache):
    """Guarda la caché en disco. Si falla (permisos, disco lleno...), no interrumpe el programa."""
    try:
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError:
        pass


def entrada_cache_valida(entrada):
    """Comprueba que una entrada de caché exista y no haya caducado."""
    if not entrada or "fecha" not in entrada or "datos" not in entrada:
        return False
    try:
        fecha = datetime.fromisoformat(entrada["fecha"])
    except ValueError:
        return False
    return datetime.now() - fecha < timedelta(days=CACHE_MAX_AGE_DAYS)


def verificar_credenciales(api_key, steam_id):
    """Hace una llamada ligera para comprobar que la key y el SteamID son válidos."""
    url = f"{BASE_URL}/ISteamUser/GetPlayerSummaries/v2/"
    params = {"key": api_key, "steamids": steam_id}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code == 401:
        raise SystemExit("API key inválida (error 401). Revísala e inténtalo de nuevo.")
    r.raise_for_status()
    players = r.json().get("response", {}).get("players", [])
    if not players:
        raise SystemExit("No se ha encontrado ningún perfil con ese SteamID64.")
    print(f"Autenticado como: {players[0].get('personaname', steam_id)}\n")

# Pausa entre llamadas para no saturar la API (logros por juego = 1-2 requests)
SLEEP_BETWEEN_CALLS = 0.4


def get_owned_games(api_key, steam_id):
    """Devuelve la lista de juegos que posees (appid, nombre, horas jugadas)."""
    url = f"{BASE_URL}/IPlayerService/GetOwnedGames/v1/"
    params = {
        "key": api_key,
        "steamid": steam_id,
        "include_appinfo": True,
        "include_played_free_games": True,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    return r.json().get("response", {}).get("games", [])


def get_player_achievements(api_key, steam_id, appid):
    """Logros del jugador para un juego. None si el juego no tiene logros."""
    url = f"{BASE_URL}/ISteamUserStats/GetPlayerAchievements/v1/"
    params = {"key": api_key, "steamid": steam_id, "appid": appid}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return None
    data = r.json().get("playerstats", {})
    if not data.get("success"):
        return None
    return data.get("achievements", [])


def get_global_achievement_percentages(appid, cache):
    """
    % global de jugadores que tiene cada logro de un juego.
    Usa la caché en disco si hay una entrada reciente para este appid.
    """
    clave = str(appid)
    entrada = cache.get(clave)
    if entrada_cache_valida(entrada):
        return entrada["datos"], True  # (datos, venía_de_caché)

    url = f"{BASE_URL}/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/"
    params = {"gameid": appid}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return {}, False
    achievements = r.json().get("achievementpercentages", {}).get("achievements", [])
    resultado = {}
    for a in achievements:
        try:
            resultado[a["name"]] = float(a["percent"])
        except (KeyError, TypeError, ValueError):
            continue  # dato corrupto o ausente para este logro, se ignora

    if resultado:
        cache[clave] = {"fecha": datetime.now().isoformat(), "datos": resultado}

    return resultado, False


def calculate_mdo(api_key, steam_id, appid, game_name, cache):
    """
    Calcula el MDO de un juego a partir de sus logros pendientes.
    Devuelve (resultado, motivo, desde_cache):
      - resultado = (mdo, logros_totales, logros_pendientes) o None
      - motivo se rellena solo cuando resultado es None, para diagnóstico
      - desde_cache indica si el % global vino de la caché local
    """
    achievements = get_player_achievements(api_key, steam_id, appid)
    if not achievements:
        return None, "sin_logros_o_perfil_privado", False

    pending = [a["apiname"] for a in achievements if a["achieved"] == 0]
    if not pending:
        return None, "completado_100", False

    percentages, desde_cache = get_global_achievement_percentages(appid, cache)
    if not percentages:
        return None, "sin_datos_globales", False

    # Dificultad de cada logro pendiente = 100 - % global que lo tiene
    dificultades = [
        100 - percentages[name] for name in pending if name in percentages
    ]
    if not dificultades:
        return None, "sin_coincidencia_logros", desde_cache

    mdo = sum(dificultades) / len(dificultades)
    return (round(mdo, 2), len(achievements), len(pending)), None, desde_cache


def pedir_filtro_horas():
    """Pregunta si se quiere aplicar un filtro de horas jugadas mínimas."""
    respuesta = input(
        "¿Quieres excluir juegos con pocas horas jugadas? (s/N): "
    ).strip().lower()
    if respuesta != "s":
        return 0.0

    while True:
        valor = input("Horas mínimas jugadas para incluir un juego (ej. 1): ").strip()
        try:
            horas = float(valor.replace(",", "."))
            if horas < 0:
                raise ValueError
            return horas
        except ValueError:
            print("Introduce un número válido (ej. 1 o 2.5).")


def exportar_csv(resultados):
    """Exporta la tabla de resultados a un CSV junto al ejecutable/script."""
    nombre_archivo = f"achievesort_resultados_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    ruta = os.path.join(APP_DIR, nombre_archivo)
    try:
        with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow(["Juego", "AppID", "MDO", "Logros pendientes", "Logros totales", "Horas jugadas"])
            for r in resultados:
                writer.writerow([
                    r["nombre"], r["appid"], r["mdo"],
                    r["pendientes"], r["total_logros"], r["horas_jugadas"],
                ])
        print(f"Resultados exportados a: {ruta}")
    except OSError as e:
        print(f"No se pudo exportar el CSV: {e}")


def main():
    api_key, steam_id = pedir_credenciales()
    verificar_credenciales(api_key, steam_id)

    horas_minimas = pedir_filtro_horas()

    cache = cargar_cache()

    print("\nObteniendo biblioteca de juegos...")
    games = get_owned_games(api_key, steam_id)

    if horas_minimas > 0:
        antes = len(games)
        games = [g for g in games if g.get("playtime_forever", 0) / 60 >= horas_minimas]
        print(f"Filtro de horas aplicado: {antes} -> {len(games)} juegos (>= {horas_minimas}h jugadas).")

    print(f"{len(games)} juegos a analizar. Consultando logros (esto puede tardar)...\n")

    resultados = []
    motivos = {}
    consultas_nuevas = 0

    for game in games:
        appid = game["appid"]
        name = game.get("name", f"App {appid}")
        horas_jugadas = round(game.get("playtime_forever", 0) / 60, 1)

        try:
            resultado, motivo, desde_cache = calculate_mdo(api_key, steam_id, appid, name, cache)
        except Exception:
            resultado, motivo, desde_cache = None, "error_inesperado", False

        # Solo esperamos entre llamadas si de verdad hemos consultado la API
        # (el endpoint de logros del jugador siempre se consulta; el de %
        # globales solo si no venía de caché)
        if not desde_cache:
            consultas_nuevas += 1
        time.sleep(SLEEP_BETWEEN_CALLS)

        if resultado is None:
            motivos[motivo] = motivos.get(motivo, 0) + 1
            continue

        mdo, total, pendientes = resultado
        resultados.append({
            "nombre": name,
            "appid": appid,
            "mdo": mdo,
            "total_logros": total,
            "pendientes": pendientes,
            "horas_jugadas": horas_jugadas,
        })

    guardar_cache(cache)

    # Ordenar de más fácil de rematar (MDO bajo) a más difícil (MDO alto)
    resultados.sort(key=lambda x: x["mdo"])

    print(f"{'Juego':<40}{'MDO':>8}{'Pendientes':>14}{'Total':>10}{'Horas':>10}")
    print("-" * 82)
    for r in resultados:
        print(f"{r['nombre'][:38]:<40}{r['mdo']:>8}{r['pendientes']:>14}{r['total_logros']:>10}{r['horas_jugadas']:>10}")

    if not resultados:
        print("No se encontró ningún juego con logros pendientes calculables.\n")
        print("Resumen de por qué se descartó cada juego:")
        etiquetas = {
            "sin_logros_o_perfil_privado": "Sin logros o el perfil no expone logros (revisa que 'Detalles del juego' esté en Público)",
            "completado_100": "Ya al 100% de logros",
            "sin_datos_globales": "Steam no devolvió estadísticas globales para ese juego",
            "sin_coincidencia_logros": "Los logros pendientes no tenían dato de % global",
            "error_inesperado": "Error inesperado al consultar este juego (se saltó automáticamente)",
        }
        for motivo, cantidad in sorted(motivos.items(), key=lambda x: -x[1]):
            print(f"  - {etiquetas.get(motivo, motivo)}: {cantidad} juegos")
    else:
        print(f"\n({consultas_nuevas} juegos consultados a la API; el resto vino de la caché local)")
        exportar_csv(resultados)


if __name__ == "__main__":
    try:
        main()
    except SystemExit as e:
        # Errores controlados (credenciales inválidas, etc.) ya traen su mensaje
        if e.code:
            print(f"\n{e.code}")
    except Exception as e:
        print(f"\nHa ocurrido un error inesperado: {e}")
    finally:
        input("\nPulsa Enter para salir...")

