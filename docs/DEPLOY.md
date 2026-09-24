# Deploy

## Pré-requisitos

- Ubuntu 24.04+
- Python 3.12+
- Docker
- systemd
- Bot Discord
- Lavalink

## Dependências Python

```bash
python3 -m venv /opt/tony-music/venv

/opt/tony-music/venv/bin/pip install \
  "discord.py[voice]" \
  "wavelink==3.5.2" \
  fastapi \
  uvicorn \
  httpx \
  python-dotenv
```

## Validar

```bash
/opt/tony-music/venv/bin/python -m py_compile /opt/tony-music/app.py
```

## Serviço

```bash
systemctl daemon-reload
systemctl enable --now tony-music
```

## Health

```bash
curl -s http://127.0.0.1:8765/health | python3 -m json.tool
```

## Playback

```bash
/opt/tony-music/venv/bin/python /opt/tony-music/ctl.py play "Hotel Lobby Migos"
/opt/tony-music/venv/bin/python /opt/tony-music/ctl.py status
```

## Diagnóstico

```bash
journalctl -u tony-music -n 100 --no-pager
docker logs --tail 100 lavalink
```
