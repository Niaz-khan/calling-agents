# Real-Time Voice Streaming — Production Runtime Guide

How to run and operate the Twilio Media Streams websocket path (added in Phase 11).

The streaming path is gated. When enabled, inbound/outbound call webhooks return
TwiML with `<Connect><Stream>` pointing at `/telephony/twilio/media`; the caller's
audio arrives over that WebSocket as G.711, is decoded, VAD-segmented, sent to
STT, and answered by the shared AI agent (tools / RAG / memory / transfer). The
reply is synthesized to audio and streamed back. When disabled, the original
Gather loop is used unchanged.

---

## 1. Required environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `VOICE_STREAMING_ENABLED` | `0` | `1` enables `<Connect><Stream>` instead of `<Gather>`. |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Must be the **publicly reachable, HTTPS** external URL of this backend. Used to build the `wss://`/`ws://` Stream URL for Twilio. |
| `DATABASE_URL` | — | PostgreSQL. |
| `JWT_SECRET_KEY` | — | Auth signing secret. |
| `LLM_API_KEY` / `LLM_MODEL` / `LLM_BASE_URL` | — | LLM provider. |
| `STT_PROVIDER` | `openai` | Whisper transcription. |
| `TTS_PROVIDER` | `edge` | Edge TTS (default) or `openai`. |
| `TTS_FORMAT` | `mp3` | Edge default. Streaming to μ-law needs ffmpeg unless you use `wav`/`pcm`. See §4. |
| `VOICE_STREAM_SPEECH_THRESHOLD` | `1000` | RMS threshold for VAD speech onset. |
| `VOICE_STREAM_END_SILENCE_SECONDS` | `0.6` | Silence duration that ends an utterance. |
| `VOICE_HEARTBEAT_SECONDS` | `20` | Twilio `mark` keepalive interval. |
| `VOICE_IDLE_TIMEOUT_SECONDS` | `300` | Close the call after this much silence. |
| `VOICE_MAX_UTTERANCE_SECONDS` | `30` | Force-finalize an overlong utterance. |

Secrets live in `.env` (git-ignored); copy `.env.example` for the documented set.

---

## 2. Serving the ASGI application

The WebSocket consumer requires an ASGI server. **`runserver` is HTTP-only.**

Start with Daphne, behind a reverse proxy when needed:

```bash
cd backend
daphne -b 0.0.0.0 -p 8000 config.asgi:application
```

Or with Gunicorn/Uvicorn driving Daphne's ASGI app — anything that serves
`config.asgi:application` over the `websocket` protocol works.

### Development over a public tunnel

Twilio needs to reach this backend over the internet:

```bash
ngrok http 8000            # gives https://<sub>.ngrok.io
```

Then in `.env`:

```env
VOICE_STREAMING_ENABLED=1
PUBLIC_BASE_URL=https://<sub>.ngrok.io
```

### Production

`PUBLIC_BASE_URL` must be the internet-facing HTTPS origin. Because it is used
to build the Stream URL, `https://` produces a `wss://` Stream (Twilio requires
TLS to initiate a Media Stream). Terminate TLS at the proxy/load balancer and
forward both HTTP and WebSocket upgrades to Daphne.

---

## 3. Twilio configuration

1. Point the number's **voice webhook** (A call comes in) at
   `https://<PUBLIC_BASE_URL>/telephony/webhook/inbound`.
2. Ensure Twilio can reach the status webhook
   (`/telephony/webhook/status`) for call lifecycle events.
3. The backend returns TwiML containing `<Connect><Stream url="wss://…">`. Media
   Streams do not require additional account settings to stream — the `wss://`
   URL must simply be reachable.
4. **Recording:** the streaming path does not emit a `<Record>` verb (which
   would conflict with `<Connect>`). Call recordings require the Twilio console
   **account/number-level recording** setting to be enabled; the resulting
   `RecordingUrl` arrives on the status webhook and is persisted onto
   `PhoneCall.recording_url`.
5. Trial numbers cannot attach custom webhooks/Media Streams. Use a provisioned,
   verified (non-trial) number.

---

## 4. ffmpeg requirement

ffmpeg is required **only** because the default Edge-TTS output is MP3 and G.711
streaming needs raw 8 kHz audio:

- Default path (`TTS_PROVIDER=edge`, `TTS_FORMAT=mp3`): ffmpeg decodes MP3 → PCM.
  Without it, streaming replies fail with a clear error. **Install ffmpeg**
  (no code change needed).
- Avoid ffmpeg entirely by using an OpenAI voice that returns linear PCM/WAV:

```env
TTS_PROVIDER=openai
TTS_FORMAT=wav
```

WAV variants are normalized in-process (`_normalize_codec`) with no ffmpeg
dependency. STT (OpenAI whisper) posts raw WAV and needs no system binary.

---

## 5. Smoke test

1. Configure §1/§3 with a live, non-trial Twilio number.
2. Verify basic health first:

```bash
curl https://<PUBLIC_BASE_URL>/health
curl https://<PUBLIC_BASE_URL>/db-health
```

3. Dial the number. You should hear the greeting, speak a request, and get a
   low-latency synthesized reply. Tool-driven flows (availability check →
   booking) go through the same code path as chat.
4. Hang up; confirm the call is finalized and the transcript/messages persisted
   in the dashboard/DB.

---

## 6. Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| Webhook returns `403` | Twilio signature validation. Confirm `TWILIO_AUTH_TOKEN` matches the account and the request hits the exact `PUBLIC_BASE_URL` host. |
| No audio / "connection timed out" | `wss://` URL unreachable. TLS must terminate before Daphne; confirm `PUBLIC_BASE_URL` is `https://`, the tunnel is up, and ports/WS upgrades are forwarded. |
| Close code `4001` | Consumer rejected the stream (missing/invalid token or callSid mismatch). Check the URL token in TwiML vs the `PhoneCall.stream_token`. |
| Close code `4403` | Auth/Token rejection — websocket connected without (or with a bad) `token`. |
| Close code `4401` | Call lookup failed — conversation/phone call does not exist yet. |
| `PytestWarning: OperationalError database test_… is being accessed` | A worker thread still holds a DB connection. Keep `_cleanup_db()`/`connections.close_all()` teardowns in tests. |
| `asyncio.TimeoutError` / `CancelledError` in tests | `ApplicationCommunicator` cancels the app task on a timed-out receive. Use single-window receives with the full budget (see `_read_media_frames`). |
| Utterance cut off mid-sentence | Lower `VOICE_STREAM_END_SILENCE_SECONDS`, or raise the speech threshold so non-speech noise doesn't split utterances. |
| "Tool not available: …" | Tool registry covers only approved tools; never arbitrary LLM strings. |

---

## 7. Non-goals

- Telnyx streaming is **not** implemented; Telnyx calls still use the Gather
  loop.
- No `<Record>` verb is emitted on the streaming path (see §3.4).