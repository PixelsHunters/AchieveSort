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
"""

import time
import requests

BASE_URL = "https://api.steampowered.com"


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


def get_global_achievement_percentages(appid):
    """% global de jugadores que tiene cada logro de un juego."""
    url = f"{BASE_URL}/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v2/"
    params = {"gameid": appid}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return {}
    achievements = r.json().get("achievementpercentages", {}).get("achievements", [])
    resultado = {}
    for a in achievements:
        try:
            resultado[a["name"]] = float(a["percent"])
        except (KeyError, TypeError, ValueError):
            continue  # dato corrupto o ausente para este logro, se ignora
    return resultado


def calculate_mdo(api_key, steam_id, appid, game_name):
    """
    Calcula el MDO de un juego a partir de sus logros pendientes.
    Devuelve (resultado, motivo):
      - resultado = (mdo, logros_totales, logros_pendientes) o None
      - motivo se rellena solo cuando resultado es None, para diagnóstico
    """
    achievements = get_player_achievements(api_key, steam_id, appid)
    if not achievements:
        return None, "sin_logros_o_perfil_privado"

    pending = [a["apiname"] for a in achievements if a["achieved"] == 0]
    if not pending:
        return None, "completado_100"

    percentages = get_global_achievement_percentages(appid)
    if not percentages:
        return None, "sin_datos_globales"

    # Dificultad de cada logro pendiente = 100 - % global que lo tiene
    dificultades = [
        100 - percentages[name] for name in pending if name in percentages
    ]
    if not dificultades:
        return None, "sin_coincidencia_logros"

    mdo = sum(dificultades) / len(dificultades)
    return (round(mdo, 2), len(achievements), len(pending)), None


def main():
    api_key, steam_id = pedir_credenciales()
    verificar_credenciales(api_key, steam_id)

    print("Obteniendo biblioteca de juegos...")
    games = get_owned_games(api_key, steam_id)
    print(f"{len(games)} juegos encontrados. Analizando logros (esto puede tardar)...\n")

    resultados = []
    motivos = {}
    for game in games:
        appid = game["appid"]
        name = game.get("name", f"App {appid}")

        try:
            resultado, motivo = calculate_mdo(api_key, steam_id, appid, name)
        except Exception:
            resultado, motivo = None, "error_inesperado"
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
        })

    # Ordenar de más fácil de rematar (MDO bajo) a más difícil (MDO alto)
    resultados.sort(key=lambda x: x["mdo"])

    print(f"{'Juego':<40}{'MDO':>8}{'Pendientes':>14}{'Total':>10}")
    print("-" * 72)
    for r in resultados:
        print(f"{r['nombre'][:38]:<40}{r['mdo']:>8}{r['pendientes']:>14}{r['total_logros']:>10}")

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

