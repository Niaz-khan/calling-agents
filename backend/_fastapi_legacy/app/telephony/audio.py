"""G.711 mu-law audio codec for Twilio media streams.

Twilio streams incoming audio as base64 mu-law (8 kHz, 8-bit). OpenAI TTS
produces WAV audio. This module converts between the two and resamples so
audio can flow between Twilio and the voice engine.
"""

import base64
import io
import struct
import wave

BIAS = 0x84
CLIP = 32635


def mulaw_to_wav(mulaw_base64: str, sample_rate: int = 8000) -> bytes:
    data = base64.b64decode(mulaw_base64)

    pcm = bytearray()

    for sample in data:
        pcm += struct.pack("<h", _decode_ulaw(sample))

    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(bytes(pcm))

    return buffer.getvalue()


def wav_to_mulaw_base64(wav_bytes: bytes, out_rate: int = 8000) -> str:
    with wave.open(io.BytesIO(wav_bytes), "rb") as wav:
        frames = wav.readframes(wav.getnframes())
        in_rate = wav.getframerate()

    count = len(frames) // 2
    samples = struct.unpack(f"<{count}h", frames[: count * 2])

    resampled = _resample(samples, in_rate, out_rate)

    encoded = bytes(_encode_ulaw(s) for s in resampled)

    return base64.b64encode(encoded).decode("ascii")


def _resample(samples: tuple[int, ...], in_rate: int, out_rate: int) -> list[int]:
    if in_rate <= 0 or out_rate <= 0:
        return list(samples)

    if in_rate == out_rate:
        return list(samples)

    ratio = in_rate / out_rate
    out_len = int(len(samples) * out_rate / in_rate)

    result: list[int] = []

    for i in range(out_len):
        position = i * ratio
        index = int(position)
        fraction = position - index

        if index + 1 < len(samples):
            value = samples[index] * (1 - fraction) + samples[index + 1] * fraction
        else:
            value = samples[index]

        result.append(int(value))

    return result


def _decode_ulaw(ulaw: int) -> int:
    ulaw = ~ulaw & 0xFF

    value = ((ulaw & 0x0F) << 3) + BIAS
    value <<= (ulaw & 0x70) >> 4

    return (value - BIAS) if (ulaw & 0x80) else (BIAS - value)


def _encode_ulaw(sample: int) -> int:
    sign = (sample >> 8) & 0x80

    if sign:
        sample = -sample

    if sample > CLIP:
        sample = CLIP

    sample += BIAS

    exponent = 0
    for shift in range(6, -1, -1):
        if sample & (0x80 << shift):
            exponent = shift
            break

    mantissa = (sample >> (exponent + 3)) & 0x0F
    value = (sign | (exponent << 4) | mantissa)

    return ~value & 0xFF