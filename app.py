import os
import asyncio
import logging
from typing import Any

import discord
import httpx
import uvicorn
import wavelink

from discord.ext import commands
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request


# ============================================================
# CONFIG
# ============================================================

load_dotenv("/opt/tony-music/.env")

DISCORD_TOKEN = os.getenv("DISCORD_MUSIC_TOKEN")

GUILD_ID = int(
    os.getenv("DISCORD_GUILD_ID")
    or os.getenv("GUILD_ID")
    or "0"
)

OWNER_ID = int(
    os.getenv("DISCORD_OWNER_ID")
    or os.getenv("OWNER_ID")
    or "0"
)

LAVALINK_URI = os.getenv(
    "LAVALINK_URI",
    "http://127.0.0.1:2333"
)

LAVALINK_PASSWORD = os.getenv("LAVALINK_PASSWORD")

API_HOST = "127.0.0.1"
API_PORT = 8765

DEFAULT_VOLUME = 50

if not DISCORD_TOKEN:
    raise RuntimeError("DISCORD_MUSIC_TOKEN não encontrado em /opt/tony-music/.env")

if not LAVALINK_PASSWORD:
    raise RuntimeError("LAVALINK_PASSWORD não encontrado em /opt/tony-music/.env")

if not GUILD_ID:
    raise RuntimeError("DISCORD_GUILD_ID não encontrado em /opt/tony-music/.env")


# ============================================================
# LOG
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

log = logging.getLogger("tony-music")


# ============================================================
# DISCORD
# ============================================================

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.voice_states = True


class TonyMusicBot(commands.Bot):

    async def setup_hook(self) -> None:
        node = wavelink.Node(
            uri=LAVALINK_URI,
            password=LAVALINK_PASSWORD
        )

        await wavelink.Pool.connect(
            nodes=[node],
            client=self
        )

        log.info("Lavalink conectado em %s", LAVALINK_URI)

    async def on_ready(self) -> None:
        log.info(
            "Discord conectado como %s (%s)",
            self.user,
            self.user.id if self.user else "?"
        )

    async def on_wavelink_node_ready(
        self,
        payload: wavelink.NodeReadyEventPayload
    ) -> None:
        log.info(
            "Lavalink Node READY | %s | resumed=%s",
            payload.node,
            payload.resumed
        )

    async def on_wavelink_track_start(
        self,
        payload: wavelink.TrackStartEventPayload
    ) -> None:
        track = payload.track

        log.info(
            "TOCANDO | %s - %s",
            track.title,
            track.author
        )

    async def on_wavelink_track_end(
        self,
        payload: wavelink.TrackEndEventPayload
    ) -> None:
        log.info(
            "TRACK END | reason=%s",
            payload.reason
        )

    async def on_wavelink_track_exception(
        self,
        payload: wavelink.TrackExceptionEventPayload
    ) -> None:
        log.error(
            "TRACK EXCEPTION | %s | %s",
            payload.track.title if payload.track else "?",
            payload.exception
        )


bot = TonyMusicBot(
    command_prefix="!",
    intents=intents
)


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title="Tony Montana Music API",
    version="2.0.0"
)

music_lock = asyncio.Lock()


# ============================================================
# HELPERS
# ============================================================

def get_guild() -> discord.Guild:
    guild = bot.get_guild(GUILD_ID)

    if guild is None:
        raise HTTPException(
            status_code=503,
            detail="Discord guild não disponível"
        )

    return guild


def track_to_dict(track: wavelink.Playable | None) -> dict | None:
    if track is None:
        return None

    return {
        "title": track.title,
        "author": track.author,
        "uri": track.uri,
        "identifier": track.identifier,
        "length": track.length,
        "source": track.source
    }


async def body_json(request: Request) -> dict[str, Any]:
    try:
        content_type = request.headers.get("content-type", "")

        if "application/json" not in content_type:
            return {}

        data = await request.json()

        if isinstance(data, dict):
            return data

    except Exception:
        pass

    return {}


def member_voice_channel(
    guild: discord.Guild,
    user_id: int
):
    member = guild.get_member(user_id)

    if member is None:
        return None

    if member.voice is None:
        return None

    return member.voice.channel


def channel_usable(
    guild: discord.Guild,
    channel
) -> bool:
    me = guild.me

    if me is None:
        return False

    perms = channel.permissions_for(me)

    return (
        perms.view_channel
        and perms.connect
        and perms.speak
    )


def find_voice_channel(
    guild: discord.Guild,
    user_id: int | None = None
):
    # 1. usuário específico recebido pela API
    if user_id:
        channel = member_voice_channel(guild, user_id)

        if channel and channel_usable(guild, channel):
            return channel

    # 2. mantém compatibilidade com o OWNER atual
    channel = member_voice_channel(guild, OWNER_ID)

    if channel and channel_usable(guild, channel):
        return channel

    # 3. se o bot já está num canal, permanece nele
    if guild.voice_client:
        current_channel = getattr(
            guild.voice_client,
            "channel",
            None
        )

        if current_channel:
            return current_channel

    # 4. procura algum canal com usuário humano
    for channel in guild.voice_channels:
        if not channel_usable(guild, channel):
            continue

        humans = [
            member
            for member in channel.members
            if not member.bot
        ]

        if humans:
            return channel

    return None


async def get_player(
    user_id: int | None = None,
    connect: bool = True
) -> wavelink.Player | None:

    guild = get_guild()

    current = guild.voice_client

    if isinstance(current, wavelink.Player):
        return current

    if not connect:
        return None

    channel = find_voice_channel(
        guild,
        user_id=user_id
    )

    if channel is None:
        raise HTTPException(
            status_code=409,
            detail=(
                "Nenhum canal de voz acessível encontrado. "
                "Entre em um canal onde o bot tenha Ver/Conectar/Falar."
            )
        )

    try:
        player: wavelink.Player = await channel.connect(
            cls=wavelink.Player,
            self_deaf=True,
            timeout=20.0
        )

    except Exception as exc:
        log.exception("Falha ao conectar no canal de voz")

        raise HTTPException(
            status_code=500,
            detail=f"Falha ao conectar no canal de voz: {exc}"
        )

    # partial:
    # toca automaticamente a fila,
    # mas NÃO adiciona recomendações sozinho.
    player.autoplay = wavelink.AutoPlayMode.partial

    await player.set_volume(DEFAULT_VOLUME)

    log.info(
        "VOICE conectado em %s",
        channel.name
    )

    return player


async def spotify_to_search(query: str) -> str:
    if "open.spotify.com/" not in query:
        return query

    try:
        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=True
        ) as client:

            response = await client.get(
                "https://open.spotify.com/oembed",
                params={"url": query}
            )

            response.raise_for_status()

            data = response.json()

            title = data.get("title", "")
            author = data.get("author_name", "")

            converted = f"{title} {author}".strip()

            if converted:
                log.info(
                    "Spotify convertido para busca: %s",
                    converted
                )

                return converted

    except Exception:
        log.exception(
            "Não foi possível converter link Spotify"
        )

    return query


async def search_tracks(
    query: str
):
    query = await spotify_to_search(query)

    # URLs do YouTube são enviadas diretamente.
    # Texto comum usa YouTube Music.
    if query.startswith(
        (
            "http://",
            "https://"
        )
    ):
        tracks = await wavelink.Playable.search(
            query,
            source=None
        )

    else:
        tracks = await wavelink.Playable.search(
            query,
            source=wavelink.TrackSource.YouTubeMusic
        )

    return tracks


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
async def root():
    return {
        "ok": True,
        "service": "Tony Montana Music API",
        "version": "2.0.0",
        "backend": "Lavalink/Wavelink"
    }


@app.get("/health")
@app.get("/healthz")
async def health():
    guild = bot.get_guild(GUILD_ID)

    player = None

    if guild and isinstance(
        guild.voice_client,
        wavelink.Player
    ):
        player = guild.voice_client

    return {
        "ok": True,
        "discord_ready": bot.is_ready(),
        "lavalink_nodes": len(wavelink.Pool.nodes),
        "voice_connected": bool(
            player and player.connected
        ),
        "playing": (
            track_to_dict(player.current)
            if player
            else None
        ),
        "queue_size": (
            player.queue.count
            if player
            else 0
        )
    }


# ============================================================
# PLAY
# ============================================================

@app.api_route(
    "/play",
    methods=["GET", "POST"]
)
async def play(
    request: Request,
    query: str | None = None,
    user_id: int | None = None
):

    data = await body_json(request)

    query = (
        query
        or data.get("query")
        or data.get("q")
        or data.get("search")
    )

    raw_user_id = (
        user_id
        or data.get("user_id")
        or data.get("userId")
    )

    if raw_user_id:
        try:
            user_id = int(raw_user_id)
        except Exception:
            user_id = None

    if not query:
        raise HTTPException(
            status_code=400,
            detail="query é obrigatório"
        )

    async with music_lock:

        player = await get_player(
            user_id=user_id,
            connect=True
        )

        assert player is not None

        try:
            results = await search_tracks(
                str(query)
            )

        except Exception as exc:
            log.exception(
                "Erro pesquisando música: %s",
                query
            )

            raise HTTPException(
                status_code=502,
                detail=f"Erro ao pesquisar música: {exc}"
            )

        if not results:
            raise HTTPException(
                status_code=404,
                detail="Nenhuma música encontrada"
            )

        # PLAYLIST
        if isinstance(
            results,
            wavelink.Playlist
        ):
            added = await player.queue.put_wait(
                results
            )

            first = (
                player.queue[0]
                if player.queue.count
                else None
            )

            if player.current is None:
                first = player.queue.get()

                await player.play(
                    first,
                    volume=player.volume or DEFAULT_VOLUME
                )

            return {
                "ok": True,
                "action": "playlist",
                "playlist": results.name,
                "added": added,
                "playing": track_to_dict(
                    player.current
                ),
                "queue_size": player.queue.count
            }

        # TRACK
        track = results[0]

        if player.current is None:
            await player.play(
                track,
                volume=player.volume or DEFAULT_VOLUME
            )

            action = "playing"

        else:
            await player.queue.put_wait(
                track
            )

            action = "queued"

        log.info(
            "%s | %s - %s",
            action.upper(),
            track.title,
            track.author
        )

        return {
            "ok": True,
            "action": action,
            "track": track_to_dict(track),
            "playing": track_to_dict(
                player.current
            ),
            "queue_size": player.queue.count
        }


# ============================================================
# PAUSE
# ============================================================

@app.api_route(
    "/pause",
    methods=["GET", "POST", "PUT"]
)
async def pause():

    async with music_lock:

        player = await get_player(
            connect=False
        )

        if not player or player.current is None:
            raise HTTPException(
                status_code=409,
                detail="Nada está tocando"
            )

        await player.pause(True)

        return {
            "ok": True,
            "paused": True
        }


# ============================================================
# RESUME
# ============================================================

@app.api_route(
    "/resume",
    methods=["GET", "POST", "PUT"]
)
async def resume():

    async with music_lock:

        player = await get_player(
            connect=False
        )

        if not player or player.current is None:
            raise HTTPException(
                status_code=409,
                detail="Nada para continuar"
            )

        await player.pause(False)

        return {
            "ok": True,
            "paused": False
        }


# ============================================================
# SKIP
# ============================================================

@app.api_route(
    "/skip",
    methods=["GET", "POST", "PUT"]
)
async def skip():

    async with music_lock:

        player = await get_player(
            connect=False
        )

        if not player or player.current is None:
            raise HTTPException(
                status_code=409,
                detail="Nada está tocando"
            )

        skipped = player.current

        next_track = (
            player.queue[0]
            if player.queue.count
            else None
        )

        await player.skip(
            force=True
        )

        return {
            "ok": True,
            "skipped": track_to_dict(
                skipped
            ),
            "next": track_to_dict(
                next_track
            ),
            "queue_size": player.queue.count
        }


# ============================================================
# STOP
# ============================================================

@app.api_route(
    "/stop",
    methods=["GET", "POST", "PUT"]
)
async def stop():

    async with music_lock:

        player = await get_player(
            connect=False
        )

        if not player:
            return {
                "ok": True,
                "stopped": True
            }

        player.queue.reset()

        if player.current:
            await player.skip(
                force=True
            )

        return {
            "ok": True,
            "stopped": True,
            "queue_size": 0
        }


# ============================================================
# LEAVE
# ============================================================

@app.api_route(
    "/leave",
    methods=["GET", "POST", "PUT", "DELETE"]
)
async def leave():

    async with music_lock:

        player = await get_player(
            connect=False
        )

        if not player:
            return {
                "ok": True,
                "disconnected": True
            }

        player.queue.reset()

        await player.disconnect()

        return {
            "ok": True,
            "disconnected": True
        }


# ============================================================
# VOLUME
# ============================================================

@app.api_route(
    "/volume",
    methods=["GET", "POST", "PUT"]
)
async def volume(
    request: Request,
    value: int | None = None,
    volume: int | None = None
):

    data = await body_json(request)

    raw = (
        value
        if value is not None
        else volume
    )

    if raw is None:
        raw = (
            data.get("value")
            if data.get("value") is not None
            else data.get("volume")
        )

    if raw is None:
        raise HTTPException(
            status_code=400,
            detail="volume é obrigatório"
        )

    try:
        raw = int(raw)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="volume inválido"
        )

    raw = max(
        0,
        min(raw, 100)
    )

    async with music_lock:

        player = await get_player(
            connect=False
        )

        if not player:
            raise HTTPException(
                status_code=409,
                detail="Bot não está no canal de voz"
            )

        await player.set_volume(raw)

        return {
            "ok": True,
            "volume": raw
        }


# ============================================================
# STATUS / FILA
# ============================================================

@app.get("/status")
async def status():

    guild = bot.get_guild(
        GUILD_ID
    )

    if guild is None:
        return {
            "ok": True,
            "discord_ready": bot.is_ready(),
            "voice_connected": False,
            "voice_channel": None,
            "playing": None,
            "queue": [],
            "volume": DEFAULT_VOLUME
        }

    player = guild.voice_client

    if not isinstance(
        player,
        wavelink.Player
    ):
        return {
            "ok": True,
            "discord_ready": bot.is_ready(),
            "voice_connected": False,
            "voice_channel": None,
            "playing": None,
            "queue": [],
            "volume": DEFAULT_VOLUME
        }

    queue = [
        track_to_dict(track)
        for track in list(player.queue)[:20]
    ]

    return {
        "ok": True,
        "discord_ready": bot.is_ready(),
        "voice_connected": player.connected,
        "voice_channel": (
            player.channel.name
            if player.channel
            else None
        ),
        "playing": track_to_dict(
            player.current
        ),
        "paused": player.paused,
        "queue": queue,
        "queue_size": player.queue.count,
        "volume": player.volume
    }


@app.get("/queue")
async def queue():

    guild = bot.get_guild(
        GUILD_ID
    )

    player = (
        guild.voice_client
        if guild
        else None
    )

    if not isinstance(
        player,
        wavelink.Player
    ):
        return {
            "ok": True,
            "queue": []
        }

    return {
        "ok": True,
        "queue": [
            track_to_dict(track)
            for track in player.queue
        ]
    }


# ============================================================
# START
# ============================================================

async def main():

    config = uvicorn.Config(
        app,
        host=API_HOST,
        port=API_PORT,
        log_level="info",
        access_log=True
    )

    server = uvicorn.Server(
        config
    )

    async with bot:
        await asyncio.gather(
            bot.start(DISCORD_TOKEN),
            server.serve()
        )


if __name__ == "__main__":
    asyncio.run(main())
