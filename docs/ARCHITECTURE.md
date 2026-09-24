# Arquitetura

## Componentes

### OpenClaw

Recebe as mensagens do Discord. Um fast-path intercepta comandos de música e chama `ctl.py`.

### ctl.py

Ponte CLI entre OpenClaw e a API.

```bash
python ctl.py play "Innerbloom"
python ctl.py pause
python ctl.py resume
python ctl.py skip
python ctl.py status
```

### FastAPI

Roda em:

```text
127.0.0.1:8765
```

### Tony Montana Music

Aplicação Discord separada, responsável por voz e playback.

### Wavelink

Camada Python que controla Lavalink.

Busca validada:

```python
wavelink.Playable.search(
    query,
    source=wavelink.TrackSource.YouTubeMusic
)
```

### Lavalink

Docker em:

```text
127.0.0.1:2333
```

### youtube-source

Snapshot validado:

```text
2be8e542d3f6f178e048dca565892684c2e40177
```

### Remote Cipher

Usado para resolver mudanças do JavaScript do player do YouTube.

No laboratório:

```text
https://cipher.kikkia.dev/
```

## Fluxo de /play

```text
POST /play
   |
   +--> localiza guild
   +--> localiza canal de voz
   +--> conecta wavelink.Player
   +--> pesquisa no YouTube Music
   +--> já existe current?
           |
           +--> não -> player.play(track)
           +--> sim -> player.queue.put_wait(track)
```

## Fila

```python
player.autoplay = wavelink.AutoPlayMode.partial
```

Assim a fila continua automaticamente, sem preencher recomendações.

## Portas

| Porta | Serviço | Exposição |
|---|---|---|
| 8765 | FastAPI | localhost |
| 2333 | Lavalink | localhost |
| 443 | Discord/YouTube | saída HTTPS |

## Permissões Discord

O bot de música precisa de:

- View Channel
- Connect
- Speak
- Use Voice Activity

Overrides de canal podem bloquear o bot mesmo quando o cargo possui permissão global.
