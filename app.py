import hashlib
import secrets
from fastapi import FastAPI, HTTPException, Query
import requests
import os

app = FastAPI(title="Bypass Service")
API_BASE = os.getenv("BYPASS_API_BASE")
BYPASS_SECRET = os.getenv("BYPASS_SECRET")

def bypass_single(url: str, android_id: str | None = None) -> str:
    """Realiza un único intento de bypass a la API de bypass.tools."""
    if android_id is None:
        android_id = secrets.token_hex(16)

    raw_id = f"{BYPASS_SECRET}:{android_id}".encode("utf-8")
    device_id = hashlib.sha256(raw_id).hexdigest()

    init_payload = {
        "deviceId": device_id,
        "platform": "android",
        "appVersion": "1.0.0",
    }
    init_response = requests.post(
        f"{API_BASE}/api/mobile/init",
        json=init_payload,
        headers={"Content-Type": "application/json"},
        timeout=15,
    )
    init_response.raise_for_status()

    session_token = init_response.json().get("sessionToken")

    bypass_payload = {"url": url, "forceRefresh": False}
    bypass_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {session_token}",
        "X-Device-ID": device_id,
    }

    bypass_response = requests.post(
        f"{API_BASE}/api/mobile/bypass",
        json=bypass_payload,
        headers=bypass_headers,
        timeout=20,
    )

    data = bypass_response.json()

    if not bypass_response.ok:
        error_msg = data.get("message", "Bypass failed")
        raise RuntimeError(error_msg)

    # Extraer el resultado en formato string
    res = data.get("result")
    if isinstance(res, dict):
        return res.get("url") or res.get("destination") or str(res)
    return str(res)


def resolve_recursive(url: str, max_depth: int = 5) -> str:
    """Ejecuta el bypass en bucle resolviendo acortadores encadenados (dobles, triples, etc.)."""
    current_url = url

    for _ in range(max_depth):
        try:
            next_url = bypass_single(current_url)

            # Si devuelve lo mismo o está vacío, ya se llegó al destino final
            if not next_url or next_url == current_url:
                break

            current_url = next_url
        except Exception:
            # Si la API falla o devuelve error, significa que la URL actual
            # ya no es un acortador soportado y es el enlace final
            break

    return current_url


@app.get("/bypass")
def get_bypass(url: str = Query(..., description="URL to bypass")):
    final_url = resolve_recursive(url)
    return {
        "status": "success",
        "original": url,
        "result": final_url,
    }
