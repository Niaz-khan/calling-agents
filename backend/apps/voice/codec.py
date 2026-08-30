"""G.711 audio codec helpers for telephony media streams.

Twilio/Telephony media streams carry 8 kHz mono audio as G.711 μ-law (PCMU)
or, for some international carriers, A-law (PCMA). Python removed the ``audioop``
module (PEP 594), so the companding tables are reimplemented here as pure
integer math.

Pipeline:

    inbound  mulaw/alaw bytes -> PCM16 -> WAV container -> STT
    outbound TTS bytes        -> PCM16 -> mulaw/alaw bytes -> websocket

The encode side searches the standard G.711 decoder mapping for the quantized
value closest to the requested sample, so whatever a conforming far end decodes
matches what we intended (and vice versa). MP3/Opus/etc. require ``ffmpeg``
(raised loudly when missing) because G.711 is not worth a heavy pure-Python
decoder.
"""

import asyncio
import struct
from dataclasses import dataclass

PCM_SAMPLE_RATE = 8000
PCM_CHANNELS = 1
PCM_BITS = 16

BIAS = 0x84


class AudioTranscodeError(Exception):
    """Raised when audio cannot be converted to/from the wire codec."""


@dataclass
class PCM:
    data: bytes
    sample_rate: int = PCM_SAMPLE_RATE
    channels: int = PCM_CHANNELS


# ---------------------------------------------------------------------------
# G.711 decoding (wire byte -> linear PCM16)
# ---------------------------------------------------------------------------


def _decode_mulaw_sample(byte: int) -> int:
    u = (~byte) & 0xFF
    t = ((u & 0x0F) << 3) + BIAS
    t <<= (u >> 4) & 0x07
    sample = t - BIAS if (u & 0x80) == 0 else BIAS - t
    return max(-32768, min(32767, sample))


def _decode_alaw_sample(byte: int) -> int:
    # Reference (Jutta Degener / Carsten Bormann, dg001) alaw2linear.
    a = byte ^ 0x55
    seg = (a >> 4) & 0x07
    t = (a & 0x0F) << 4
    if seg == 0:
        t += 8
    else:
        t += 0x108
        if seg > 1:
            t <<= seg - 1
    return max(-32768, min(32767, t if (a & 0x80) else -t))


def decode_mulaw(payload: bytes) -> bytes:
    """Convert μ-law wire bytes into little-endian PCM16 (8 kHz mono)."""
    return struct.pack(
        f"<{len(payload)}h", *(_decode_mulaw_sample(b) for b in payload)
    )


def decode_alaw(payload: bytes) -> bytes:
    """Convert A-law wire bytes into little-endian PCM16 (8 kHz mono)."""
    return struct.pack(
        f"<{len(payload)}h", *(_decode_alaw_sample(b) for b in payload)
    )


def decode_codec(payload: bytes, codec: str) -> bytes:
    codec = _normalize_codec(codec)
    if codec == "mulaw":
        return decode_mulaw(payload)
    if codec == "alaw":
        return decode_alaw(payload)
    if codec == "pcm16":
        return payload
    raise AudioTranscodeError(f"Unsupported inbound codec: {codec}")


# ---------------------------------------------------------------------------
# G.711 encoding (linear PCM16 -> wire byte)
# ---------------------------------------------------------------------------

def _mulaw_encode_sample(sample: int) -> int:
    negative = sample < 0
    magnitude = -sample if negative else sample
    magnitude = min(magnitude, 32635)

    best_u = 0
    best_error = magnitude + 1
    for exponent in range(8):
        base = (0x84) << exponent  # mantissa 0
        for mantissa in range(16):
            quantized = ((mantissa << 3 | 0x84) << exponent) - BIAS
            error = abs(quantized - magnitude)
            if error < best_error:
                best_error = error
                best_u = (exponent << 4) | mantissa
                if error == 0:
                    break
        if best_error == 0:
            break

    u = (0x80 if negative else 0) | best_u
    return (~u) & 0xFF


def _alaw_encode_sample(sample: int) -> int:
    # Nearest-quantized search over the standard decoder mapping. A-law is
    # second-class (Twilio streams μ-law in North America); preferring a
    # deterministic minimum-error byte over a hand-derived segment table keeps
    # the wire format in sync with whatever conforming decoder we pair with.
    best_byte = 0xD5
    best_error = abs(_decode_alaw_sample(0xD5) - sample)
    for byte in range(256):
        error = abs(_decode_alaw_sample(byte) - sample)
        if error < best_error:
            best_error = error
            best_byte = byte
            if error == 0:
                break
    return best_byte


def encode_mulaw(pcm: bytes) -> bytes:
    """Convert little-endian PCM16 into μ-law wire bytes."""
    if len(pcm) % 2:
        raise AudioTranscodeError("PCM16 payload length must be even")
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    return bytes(_mulaw_encode_sample(s) for s in samples)


def encode_alaw(pcm: bytes) -> bytes:
    """Convert little-endian PCM16 into A-law wire bytes."""
    if len(pcm) % 2:
        raise AudioTranscodeError("PCM16 payload length must be even")
    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    return bytes(_alaw_encode_sample(s) for s in samples)


def encode_codec(pcm: bytes, codec: str) -> bytes:
    codec = _normalize_codec(codec)
    if codec == "mulaw":
        return encode_mulaw(pcm)
    if codec == "alaw":
        return encode_alaw(pcm)
    if codec == "pcm16":
        return pcm
    raise AudioTranscodeError(f"Unsupported outbound codec: {codec}")


def _normalize_codec(codec: str) -> str:
    value = (codec or "").strip().lower().replace("_", "-").replace("/", "-")
    if value in ("mulaw", "pcmu", "audio-x-mulaw", "audio-x-pcmu", "audio-basic"):
        return "mulaw"
    if value in ("alaw", "pcma", "audio-x-alaw", "audio-x-pcma"):
        return "alaw"
    if value in ("pcm16", "pcm", "l16", "audio-pcm", "audio-x-raw", "audio-raw"):
        return "pcm16"
    if value in ("wav", "wave", "audio-wav", "audio-x-wav", "audio-wave"):
        return "wav"
    return value


# ---------------------------------------------------------------------------
# PCM16 helpers
# ---------------------------------------------------------------------------


def wrap_wav(pcm: bytes, sample_rate: int = PCM_SAMPLE_RATE) -> bytes:
    """Wrap raw PCM16 into a RIFF/WAVE container for STT (whisper reads wav)."""
    if len(pcm) % 2:
        raise AudioTranscodeError("PCM16 payload length must be even")
    data_size = len(pcm)
    byte_rate = sample_rate * PCM_CHANNELS * (PCM_BITS // 8)
    block_align = PCM_CHANNELS * (PCM_BITS // 8)

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + data_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        PCM_CHANNELS,
        sample_rate,
        byte_rate,
        block_align,
        PCM_BITS,
        b"data",
        data_size,
    )
    return header + pcm


def resample_pcm16(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Linearly resample mono PCM16 (handles 24 kHz TTS -> 8 kHz wire)."""
    if src_rate == dst_rate:
        return pcm
    if len(pcm) % 2:
        raise AudioTranscodeError("PCM16 payload length must be even")

    samples = struct.unpack(f"<{len(pcm) // 2}h", pcm)
    count_in = len(samples)
    count_out = max(1, int(count_in * dst_rate / src_rate))
    ratio = src_rate / dst_rate
    out = []
    for index in range(count_out):
        position = index * ratio
        left = int(position)
        right = min(left + 1, count_in - 1)
        frac = position - left
        sample = samples[left] + int((samples[right] - samples[left]) * frac)
        out.append(max(-32768, min(32767, sample)))
    return struct.pack(f"<{len(out)}h", *out)


# ---------------------------------------------------------------------------
# Output transcoding (TTS bytes -> wire codec)
# ---------------------------------------------------------------------------


def _pcm_from_raw(audio: bytes, content_type: str, sample_rate: int) -> bytes:
    rate = sample_rate or PCM_SAMPLE_RATE
    return resample_pcm16(audio, rate, PCM_SAMPLE_RATE)


def _pcm_from_wav(audio: bytes) -> bytes:
    if len(audio) < 44 or audio[:4] != b"RIFF" or audio[8:12] != b"WAVE":
        raise AudioTranscodeError("Invalid WAV payload")
    sample_rate = struct.unpack_from("<I", audio, 24)[0]
    bits = struct.unpack_from("<H", audio, 34)[0]
    channels = struct.unpack_from("<H", audio, 22)[0]
    data_offset = 44
    # Walk chunks to find the actual data chunk (fmt may have extra bytes).
    offset = 12
    while offset + 8 <= len(audio):
        chunk_id = audio[offset:offset + 4]
        size = struct.unpack_from("<I", audio, offset + 4)[0]
        if chunk_id == b"data":
            data_offset = offset + 8
            break
        offset += 8 + size + (size % 2)
    pcm = audio[data_offset:]
    if channels != 1 or bits != 16:
        raise AudioTranscodeError("Only mono 16-bit WAV is supported")
    return resample_pcm16(pcm, sample_rate, PCM_SAMPLE_RATE)


async def transcode_audio_to_codec(
    audio: bytes,
    content_type: str,
    codec: str = "mulaw",
) -> bytes:
    """Turn TTS bytes (wav/raw/mp3/mpeg/opus) into wire codec bytes.

    ``audio/x-mulaw`` and ``audio/x-alaw`` pass through unchanged; PCM/WAV are
    resampled and encoded in-process; every other format (mp3/opus/...) is
    decoded with ``ffmpeg``, which must be installed.
    """
    normalized = _normalize_codec(content_type)
    target = _normalize_codec(codec)

    if normalized == target:
        return audio

    if normalized == "mulaw":
        return audio if target == "mulaw" else encode_codec(decode_mulaw(audio), target)
    if normalized == "alaw":
        return audio if target == "alaw" else encode_codec(decode_alaw(audio), target)

    if normalized == "pcm16":
        rate = _rate_from_content_type(content_type)
        pcm = _pcm_from_raw(audio, content_type, rate)
        return encode_codec(pcm, target)

    if normalized in ("wav", "wave"):
        pcm = _pcm_from_wav(audio)
        return encode_codec(pcm, target)

    pcm = await _ffmpeg_decode_to_pcm(audio)
    return encode_codec(pcm, target)


def _rate_from_content_type(content_type: str) -> int:
    for part in content_type.split(";"):
        part = part.strip()
        if part.lower().startswith("rate="):
            try:
                return int(part.split("=", 1)[1].strip())
            except (ValueError, IndexError):
                break
    return PCM_SAMPLE_RATE


async def _ffmpeg_decode_to_pcm(audio: bytes) -> bytes:
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        "pipe:0",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        "8000",
        "pipe:1",
    ]
    try:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise AudioTranscodeError(
            "ffmpeg is required to convert this TTS format to G.711; install "
            "ffmpeg or configure a TTS provider that returns raw PCM/WAV "
            "audio."
        ) from exc

    stdout, stderr = await process.communicate(audio)

    if process.returncode != 0 or not stdout:
        detail = stderr.decode(errors="replace")[:200]
        raise AudioTranscodeError(f"ffmpeg failed: {detail}")

    return stdout