def transcribe_audio(audio_path, whisper_model):
    """Whisper 转写"""
    segments, info = whisper_model.transcribe(str(audio_path), beam_size=5, language="zh")
    raw_transcript = ""
    segments_raw = []
    for seg in segments:
        line = f"[{seg.start:.2f}s -> {seg.end:.2f}s] {seg.text}"
        raw_transcript += line + "\n"
        segments_raw.append((seg.start, seg.end, seg.text))
    return raw_transcript, segments_raw, info