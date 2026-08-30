"""Tests for the pure-Python G.711 codec helpers (voice.codec)."""

import asyncio
import struct

import pytest

from .codec import (
    AudioTranscodeError,
    PCM_SAMPLE_RATE,
    decode_alaw,
    decode_codec,
    decode_mulaw,
    encode_alaw,
    encode_codec,
    encode_mulaw,
    resample_pcm16,
    transcode_audio_to_codec,
    wrap_wav,
)

pytestmark = pytest.mark.django_db


def test_mulaw_silence_and_wire_ponies():
    # 0xFF (μ-law) and 0x7F (μ-law extended) both decode to zero.
    assert decode_mulaw(b"\xff") == b"\x00\x00"
    assert decode_mulaw(b"\x7f") == b"\x00\x00"
    # -1 PCM16 encodes to the extended silence word 0x7F.
    assert encode_mulaw(b"\xff\xff") == b"\x7f"
    # PCM zero encodes to 0xFF.
    assert encode_mulaw(b"\x00\x00") == b"\xff"


def test_mulaw_round_trip_bounded_error():
    samples = [i * 257 for i in range(-127, 128)] + [0, 1, -1, 32767, -32768]
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    decoded = struct.unpack(f"<{len(samples)}h", decode_mulaw(encode_mulaw(pcm)))
    worst = max(abs(a - b) for a, b in zip(samples, decoded))
    # G.711 μ-law's worst step is ~640 out of a ±32768 range.
    assert worst <= 800


def test_alaw_silence_byte():
    # The A-law silence word is 0xD5; PCM zero must encode to it.
    assert encode_alaw(b"\x00\x00") == b"\xd5"
    # And it must round-trip through the encoder/decoder pair.
    assert encode_alaw(decode_alaw(b"\xd5")) == b"\xd5"


def test_alaw_round_trip_bounded_error():
    samples = [i * 257 for i in range(-127, 128)] + [0, 1, -1, 32767, -32768]
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    decoded = struct.unpack(f"<{len(samples)}h", decode_alaw(encode_alaw(pcm)))
    worst = max(abs(a - b) for a, b in zip(samples, decoded))
    assert worst <= 1200


def test_codec_dispatch_and_validation():
    pcm = b"\x00\x00\xff\x7f"
    assert encode_codec(pcm, "mulaw") == encode_mulaw(pcm)
    assert encode_codec(pcm, "alaw") == encode_alaw(pcm)
    assert encode_codec(pcm, "pcm16") == pcm
    assert decode_codec(encode_mulaw(pcm), "audio/x-mulaw") == decode_mulaw(encode_mulaw(pcm))
    assert decode_codec(pcm, "l16") == pcm

    with pytest.raises(AudioTranscodeError):
        encode_codec(pcm, "opus")
    with pytest.raises(AudioTranscodeError):
        decode_codec(pcm, "opus")
    with pytest.raises(AudioTranscodeError):
        encode_mulaw(b"\x00")  # odd length


def test_wrap_wav_header():
    pcm = b"\x00\x00" * 1600
    wav = wrap_wav(pcm)
    assert wav[:4] == b"RIFF"
    assert wav[8:12] == b"WAVE"
    assert struct.unpack_from("<H", wav, 22)[0] == 1  # mono
    assert struct.unpack_from("<I", wav, 24)[0] == PCM_SAMPLE_RATE
    assert struct.unpack_from("<H", wav, 34)[0] == 16  # bits
    assert len(wav) == 44 + len(pcm)


def test_resample_pcm16_downsample():
    samples = [550 * (i % 50) for i in range(24000)]
    pcm = struct.pack(f"<{len(samples)}h", *samples)
    out = resample_pcm16(pcm, 24000, 8000)
    assert len(out) == 8000 * 2


def test_transcode_passthrough_mulaw():
    payload = encode_mulaw(b"\x00\x00" * 100)
    assert asyncio.run(
        transcode_audio_to_codec(payload, "audio/x-mulaw", "mulaw")
    ) == payload


def test_transcode_wav_to_mulaw():
    pcm = b"\x00\x00" * 800
    wav = wrap_wav(pcm)
    result = asyncio.run(transcode_audio_to_codec(wav, "audio/wav", "mulaw"))
    assert len(result) == 800
    assert decode_mulaw(result) == b"\x00\x00" * 800


def test_transcode_missing_ffmpeg_raises_clear_error(monkeypatch):
    async def boom(*args, **kwargs):
        raise FileNotFoundError()

    monkeypatch.setattr("apps.voice.codec.asyncio.create_subprocess_exec", boom)

    with pytest.raises(AudioTranscodeError) as exc:
        asyncio.run(transcode_audio_to_codec(b"id3mp3", "audio/mpeg", "mulaw"))

    assert "ffmpeg" in str(exc.value)