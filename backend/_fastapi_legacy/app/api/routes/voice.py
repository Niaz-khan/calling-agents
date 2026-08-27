import base64
import asyncio
import json

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.security import decode_access_token
from app.database import get_db
from app.models.agent import Agent
from app.models.call import Call, CallDirection, CallStatus
from app.models.user import User
from app.services.customers import create_customer
from app.services.voice_session import (
    EmptyUtteranceError,
    UtteranceBuffer,
    VoiceSessionEngine,
)
from app.voice.stt import get_stt_provider
from app.voice.tts import get_tts_provider

from app.config import settings


router = APIRouter(
    prefix="/voice",
    tags=["voice"],
)

AUDIO_CHUNK_BYTES = 16 * 1024


def _authenticate_user(db: Session, token: str) -> User | None:
    try:
        user_id = decode_access_token(token)
    except Exception:
        return None

    return db.get(User, user_id)


def _get_user_agent(db: Session, user: User, agent_id: int) -> Agent | None:
    return db.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.owner_id == user.id,
            Agent.is_active.is_(True),
        )
    )


def _create_voice_call(
    db: Session,
    user: User,
    agent: Agent,
    caller_number: str,
) -> Call:
    customer = create_customer(
        db=db,
        owner_id=user.id,
        phone_number=caller_number,
    )

    call = Call(
        agent_id=agent.id,
        customer_id=customer.id,
        caller_number=caller_number,
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
    )

    db.add(call)
    db.commit()
    db.refresh(call)

    return call


@router.websocket("/ws")
async def voice_ws(
    websocket: WebSocket,
    token: str,
    db: Session = Depends(get_db),
):
    await websocket.accept()

    user = _authenticate_user(db, token)

    if user is None:
        await websocket.send_json({"type": "error", "detail": "Unauthorized"})
        await websocket.close(code=4401)
        return

    engine: VoiceSessionEngine | None = None
    utterance = UtteranceBuffer()
    playback_task: asyncio.Task | None = None
    content_type = "audio/wav"
    language: str | None = None
    send_lock = asyncio.Lock()

    def cancel_playback() -> None:
        nonlocal playback_task
        if playback_task is not None and not playback_task.done():
            playback_task.cancel()

    async def send_json(payload: dict) -> None:
        async with send_lock:
            await websocket.send_json(payload)

    try:
        while True:
            try:
                message = await websocket.receive()
            except WebSocketDisconnect:
                break

            if message.get("type") == "websocket.disconnect":
                break

            data = message.get("text")

            if message.get("bytes") is not None:
                cancel_playback()
                if playback_task is not None and not playback_task.done():
                    await send_json({"type": "playback_interrupted"})
                utterance.append(message["bytes"])
                continue

            if data is None:
                continue

            try:
                payload = json.loads(data)
            except json.JSONDecodeError:
                continue

            msg_type = payload.get("type")

            if msg_type == "session_start":
                if engine is not None:
                    await send_json({"type": "error", "detail": "Session already started"})
                    continue

                agent_id = payload.get("agent_id")
                caller_number = payload.get("caller_number")

                if not agent_id or not caller_number:
                    await send_json(
                        {"type": "error", "detail": "agent_id and caller_number required"}
                    )
                    continue

                agent = _get_user_agent(db, user, agent_id)

                if agent is None:
                    await send_json({"type": "error", "detail": "Agent not found"})
                    continue

                call = _create_voice_call(db, user, agent, caller_number)
                engine = VoiceSessionEngine(
                    db=db,
                    call=call,
                    agent=agent,
                    stt_provider=get_stt_provider(),
                    tts_provider=get_tts_provider(),
                )
                language = payload.get("language")
                content_type = payload.get("content_type", "audio/wav")

                await send_json({"type": "session_started", "call_id": call.id})

            elif msg_type == "utterance_end":
                if engine is None or utterance.is_empty:
                    continue

                audio = utterance.snapshot()
                utterance.clear()

                async def handle_utterance(audio_bytes: bytes) -> None:
                    try:
                        turn = await engine.process_utterance(
                            audio_bytes,
                            content_type=content_type,
                            language=language,
                        )

                        await send_json({"type": "stt_result", "text": turn.user_text})
                        await send_json(
                            {"type": "assistant_text", "text": turn.assistant_text}
                        )

                        audio_data = turn.audio
                        for offset in range(0, len(audio_data), AUDIO_CHUNK_BYTES):
                            chunk = audio_data[offset : offset + AUDIO_CHUNK_BYTES]
                            await send_json(
                                {
                                    "type": "audio",
                                    "content_type": turn.content_type,
                                    "data": base64.b64encode(chunk).decode("ascii"),
                                }
                            )
                        await send_json({"type": "audio_end"})
                    except EmptyUtteranceError:
                        await send_json({"type": "error", "detail": "No speech detected"})
                    except Exception:
                        await send_json(
                            {"type": "error", "detail": "Failed to process utterance"}
                        )

                playback_task = asyncio.create_task(handle_utterance(audio))

            elif msg_type == "interrupt":
                cancel_playback()
                await send_json({"type": "playback_interrupted"})

            elif msg_type == "heartbeat":
                await send_json({"type": "heartbeat"})

    finally:
        cancel_playback()