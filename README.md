# Tony Montana Music

Bot de música para Discord integrado ao **OpenClaw**, com backend em **FastAPI + discord.py + Wavelink + Lavalink**.

O projeto separa o bot principal de IA do bot de voz. O usuário conversa com o **Tony Montana** no Discord; o OpenClaw identifica os comandos de música e chama uma API local; o **Tony Montana Music** entra no canal de voz e reproduz o áudio.

## Arquitetura

```text
Usuário no Discord
        |
        v
Tony Montana (OpenClaw)
        |
        | fast-path / ctl.py
        v
FastAPI :8765
        |
        v
Wavelink 3.5.2
        |
        v
Lavalink 4.2.2 :2333
        |
        v
youtube-source
        |
        +--> OAuth com conta secundária
        |
        +--> remoteCipher
        |
        v
YouTube / YouTube Music
        |
        v
Tony Montana Music
        |
        v
Discord Voice
```

## Stack validada

- Ubuntu Server 24.04
- Python 3.12
- discord.py 2.7.1
- Wavelink 3.5.2
- Lavalink 4.2.2
- youtube-source snapshot `2be8e542d3f6f178e048dca565892684c2e40177`
- FastAPI
- Uvicorn
- systemd
- Docker
- OpenClaw

## Funcionalidades

A API local roda em `127.0.0.1:8765`.

| Endpoint | Método | Função |
|---|---|---|
| `/health` | GET | Saúde do Discord, Lavalink, voice e fila |
| `/play` | POST/GET | Toca ou adiciona à fila |
| `/pause` | POST/GET/PUT | Pausa |
| `/resume` | POST/GET/PUT | Continua |
| `/skip` | POST/GET/PUT | Pula |
| `/stop` | POST/GET/PUT | Para e limpa a fila |
| `/leave` | POST/GET/PUT/DELETE | Sai do canal |
| `/volume` | POST/GET/PUT | Ajusta volume |
| `/status` | GET | Estado atual |
| `/queue` | GET | Fila atual |

Quando uma música já está tocando, um novo `/play` não corta a música atual: a nova faixa entra na fila.

## Comandos pelo OpenClaw

```text
@Tony toca Hotel Lobby Migos
@Tony toca Innerbloom
@Tony pausa
@Tony continua
@Tony pula
@Tony volume 30
@Tony para
```

A política atual permite que membros do servidor utilizem os comandos de música.

## Estrutura sugerida

```text
tony-montana-music/
├── app.py
├── ctl.py
├── .env.example
├── .gitignore
├── README.md
├── SECURITY.md
├── docs/
│   ├── ARCHITECTURE.md
│   └── DEPLOY.md
└── lavalink/
    └── application.example.yml
```

## Variáveis de ambiente

```dotenv
DISCORD_MUSIC_TOKEN=COLOQUE_O_TOKEN_AQUI
DISCORD_GUILD_ID=SEU_GUILD_ID
DISCORD_OWNER_ID=SEU_USER_ID
LAVALINK_URI=http://127.0.0.1:2333
LAVALINK_PASSWORD=TROQUE_POR_UMA_SENHA_FORTE
```

Nunca faça commit do `.env`.

## Lavalink

O Lavalink deve ficar exposto somente localmente:

```text
127.0.0.1:2333
```

A configuração validada usa OAuth, youtube-source snapshot e remoteCipher.

Erros encontrados durante o desenvolvimento:

```text
Sign in to confirm you're not a bot
This video requires login
Must find sig function from script
```

A solução validada foi:

1. OAuth com conta Google secundária.
2. youtube-source em snapshot.
3. remoteCipher.
4. Busca via `TrackSource.YouTubeMusic`.

## Testes

```bash
systemctl status tony-music --no-pager -l
curl -s http://127.0.0.1:8765/health | python3 -m json.tool
/opt/tony-music/venv/bin/python /opt/tony-music/ctl.py play "Hotel Lobby Migos"
/opt/tony-music/venv/bin/python /opt/tony-music/ctl.py status
journalctl -u tony-music -f
```

## Segurança

Nunca publique:

- `.env`
- Discord bot token
- Google OAuth refresh token
- cookies do YouTube
- WireGuard private key
- WireGuard preshared key
- `youtube-cookies.txt`
- `application.yml` real contendo `refreshToken`

Veja `SECURITY.md`.

## Estado atual

- FastAPI: OK
- Discord Gateway: OK
- Discord Voice: OK
- Wavelink -> Lavalink: OK
- Pesquisa YouTube Music: OK
- OAuth: OK
- remoteCipher: OK
- Reprodução de áudio: OK
- Fila: habilitada

## Próximos passos

- Passar o `user_id` do solicitante para `/play`.
- Entrar automaticamente no canal de voz de quem pediu.
- Opcional: cargo `DJ` para comandos destrutivos.
- Mensagens melhores no Discord.
- Hospedar o `yt-cipher` localmente.
- Healthcheck e monitoramento.
- Rotação segura de credenciais.

## Licença

Defina a licença antes de tornar o repositório público.
