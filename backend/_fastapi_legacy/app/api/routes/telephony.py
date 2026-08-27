import json
import base64

from fastapi import APIRouter, Depends, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.call import Call, CallDirection, CallStatus
from app.models.customer import Customer
from app.models.phone_number import PhoneNumber
from app.models.user import User
from app.schemas.phone_number import PhoneNumberCreate
from app.services.call_intelligence import finalize_call
from app.services.calls import run_agent_turn
from app.services.telephony import (
    resolve_phone_number,
    create_inbound_call,
    apply_provider_status,
)
from app.telephony.twilio import (
    validate_twilio_signature,
    build_greeting_twiml,
    build_stream_twiml,
    build_hangup_twiml,
)
from app.services.voice_session import VoiceSessionEngine, VoiceTurnResult
from app.voice.base import STTResult, TTSResult
from app.voice.stt import get_stt_provider
from app.voice.tts import get_tts_provider


router = APIRouter(
    prefix="/telephony",
    tags=["telephony"],
)


def _ws_url(path: str) -> str:
    """Compute WebSocket URL from public_base_url."""
    base = settings.public_base_url.rstrip("/")
    scheme = "wss" if base.startswith("https") else "ws"
    return f"{scheme}://{base}{path}"


def _get_user_agent(db: Session, user: User, agent_id: int) -> Agent | None:
    return db.scalar(
        Agent.__table__.select().where(Agent.id == agent_id, Agent.owner_id == user.id, Agent.is_active.is_(True))
    )


def _authenticate_user(db: Session, token: str) -> User | None:
    try:
        user_id = settings.decode_access_token(token)  # reuse existing decode
    except Exception:
        return None
    return db.get(User, user_id)


@router.post("/webhook/inbound", include_in_schema=False)
async def inbound_webhook(request: Request, db: Session = Depends(get_db)):
    """Twilio inbound voice webhook.

    Verifies signature, resolves phone number, creates/connects call,
    and returns TwiML to start the media stream.
    """
    form = await request.form()
    url = str(request.url)
    signature = request.headers.get("X-Twilio-Signature", "")

    if not validate_twilio_signature(
        url,
        {k: v for k, v in form.items()},
        signature,
        settings.twilio_auth_token,
    ):
        raise status.HTTP_403_FORBIDDEN

    provider_call_id = form.get("CallSid", "")
    to_number = form.get("To", "")
    from_number = form.get("From", "")

    # 1️⃣ Try to match an existing call (outbound leg answered)
    call = db.scalar(
        RequestSelect(Call).where(Call.provider_call_id == provider_call_id)
    ) if provider_call_id else None

    if call is None:
        # 2️⃣ Inbound: find phone number by called number
        phone_number = resolve_phone_number(db, to_number)
        if phone_number is None:
            return Response(
                content=build_hangup_twiml(),
                media_type="application/xml",
                status_code=404,
            )

        call = create_inbound_call(db, phone_number, from_number, provider_call_id)

    # 3️⃣ Build media stream URL and TwiML
    stream_url = _ws_url(f"/telephony/media/{call.id}")

    twiml = build_greeting_twiml(
        "Hello! Welcome to our business. How can I help you?",
        stream_url,
        provider_call_id,
    )

    return Response(content=twiml, media_type="application/xml")


@router.post("/webhook/status", include_in_schema=False)
async def status_webhook(request: Request, db: Session = Depends(get_db)):
    """Twilio status callback.

    Normalizes provider status into our CallStatus and finalizes the call
    when the call ends or fails.
    """
    form = await request.form()
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)

    if not validate_twilio_signature(
        url,
        {k: str(v) for k, v in form.items()},
        signature,
        settings.twilio_auth_token,
    ):
        raise status.HTTP_403_FORBIDDEN

    provider_call_id = form.get("CallSid", "")
    provider_status = form.get("CallStatus", "").lower()

    call = apply_provider_status(db, provider_call_id, provider_status)
    if call is not None:
        db.commit()

    return {"ok": True}


@router.websocket("/media/{call_id}")
async def media_ws(websocket: WebSocket, call_id: int, db: Session = Depends(get_db)):
    """Twilio Media Streams WebSocket.

    Receives inbound audio (mu-law 8kHz) and sends outbound TTS audio
    (mulaw-encoded) back to Twilio. Drives the VoiceSessionEngine.
    """
    await websocket.accept()

    call = db.get(Call, call_id)
    if call is None:
        await websocket.close(code=4404)
        return

    agent = db.get(Agent, call.agent_id)
    if agent is None:
        await websocket.close(code=404)
        return

    engine = VoiceSessionEngine(
        db=db,
        call=call,
        agent=agent,
        stt_provider=get_stt_provider(),
        tts_provider=get_tts_provider(),
    )

    utterance = VoiceSessionEngine.UtteranceBuffer()
    outbound_task: object | None = None  # will hold asyncio.Task
    interrupted = False

    def cancel_outbound():
        nonlocal outbound_task, interrupted
        if outbound_task is not None and not outbound_task.done():
            outbound_task.cancel()
        interrupted = True

    try:
        while True:
            msg = await websocket.receive_json()

            event = msg.get("event")

            if event == "start":
                stream_sid = msg["streamSid"]
                # Acknowledge connection; Twilio expects a brief JSON ack
                await websocket.send_json(
                    {"event": "connected", "streamSid": stream_sid, "status": "connected"}
                )

            elif event == "media":
                # Inbound audio from Twilio (mu-law 8kHz)
                payload_b64 = msg["media"]["payload"]
                utterance.append(base64.b64decode(payload_b64))

            elif event == "stop":
                # End of utterance — process what we have
                if utterance.size > 0 and not interrupted:
                    audio_bytes = utterance.snapshot()
                    utterance.clear()

                    try:
                        turn: VoiceTurnResult = await engine.process_utterance(
                            audio_bytes,
                            content_type="audio/wav",
                        )

                        # Send TTS audio back to Twilio as mulaw chunks
                        mulaw_data = base64.b64encode(
                            engine.synthesize(turn.assistant_text).audio
                        ).decode()

                        # Send in mulaw 8kHz chunks so Twilio can play them progressively
                        chunk_size = 160  # ~10ms at 8kHz mono 8-bit
                        for i in range(0, len(mulaw_data), chunk_size):
                            chunk_b64 = base64.b64encode(
                                mulaw_data[i : i + chunk_size]
                            ).decode()
                            await websocket.send_json(
                                {
                                    "event": "media",
                                    "media": {"payload": chunk_b64, "track": "outbound"},
                                }
                            )
                        # Mark end of this utterance's audio
                        await websocket.send_json(
                            {"event": "media", "media": {"payload": "", "track": "outbound"}, "status": "finished"}
                        )
                    except Exception as e:
                        await websocket.send_json({"event": "error", "message": str(e)})

                # Clear buffer for next utterance
                utterance.clear()

            elif event == "hangup":
                # Customer hung up — end the call loop
                break

            elif event == "interrupt":
                # Customer started talking while AI was speaking
                cancel_outbound()
                await websocket.send_json({"event": "interrupted"})

    finally:
        cancel_outbound()