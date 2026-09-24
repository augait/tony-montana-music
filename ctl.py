import json
import sys

import httpx


BASE = "http://127.0.0.1:8765"


def show(response):
    try:
        print(
            json.dumps(
                response.json(),
                indent=2,
                ensure_ascii=False,
            )
        )
    except Exception:
        print(response.text)

    if response.status_code >= 400:
        sys.exit(1)


if len(sys.argv) < 2:
    print(
        "Uso: ctl.py "
        "play|pause|resume|skip|stop|leave|status|volume"
    )
    sys.exit(1)


command = sys.argv[1].lower()


if command == "play":

    if len(sys.argv) < 3:
        print("Informe a música ou link.")
        sys.exit(1)

    query = " ".join(sys.argv[2:])

    response = httpx.post(
        f"{BASE}/play",
        json={"query": query},
        timeout=60,
    )


elif command == "pause":

    response = httpx.post(
        f"{BASE}/pause",
        timeout=10,
    )


elif command == "resume":

    response = httpx.post(
        f"{BASE}/resume",
        timeout=10,
    )


elif command == "skip":

    response = httpx.post(
        f"{BASE}/skip",
        timeout=10,
    )


elif command == "stop":

    response = httpx.post(
        f"{BASE}/stop",
        timeout=10,
    )


elif command == "leave":

    response = httpx.post(
        f"{BASE}/leave",
        timeout=10,
    )


elif command == "status":

    response = httpx.get(
        f"{BASE}/status",
        timeout=10,
    )


elif command == "volume":

    if len(sys.argv) != 3:
        print("Exemplo: ctl.py volume 30")
        sys.exit(1)

    response = httpx.post(
        f"{BASE}/volume",
        json={
            "volume": int(sys.argv[2])
        },
        timeout=10,
    )


else:
    print(f"Comando inválido: {command}")
    sys.exit(1)


show(response)
