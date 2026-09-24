# Security

## Nunca versionar segredos

Não faça commit de:

```text
.env
DISCORD_MUSIC_TOKEN
OAuth refresh token
youtube-cookies.txt
WireGuard PrivateKey
WireGuard PresharedKey
VPN credentials
application.yml real com refreshToken
```

## Se um segredo foi exposto

1. Revogue a credencial.
2. Gere uma nova.
3. Atualize o servidor.
4. Confirme que ela não entrou no histórico Git.
5. Não reutilize a credencial antiga.

## Lavalink

Mantenha em:

```text
127.0.0.1:2333
```

## FastAPI

Mantenha em:

```text
127.0.0.1:8765
```

Se futuramente exposto, adicione autenticação, TLS, rate limiting e autorização.

## Discord

Use somente permissões necessárias. Evite `Administrator`.

## OpenClaw

Comandos públicos de música não devem significar acesso administrativo ou shell.

## Pré-commit

```bash
git status
git diff --cached

grep -RniE \
  'refreshToken|DISCORD_MUSIC_TOKEN|PrivateKey|PresharedKey|youtube-cookies|BEGIN PRIVATE KEY' \
  . \
  --exclude-dir=.git
```

Revise qualquer ocorrência antes do push.
