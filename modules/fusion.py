def fuse(segments_raw, captions, fps, total_frames):
    """时间戳对齐融合"""
    merged = "# 视频完整上下文\n\n"
    
    def get_frame_at_time(t):
        frame_num = int(t * fps) + 1
        if frame_num > total_frames:
            frame_num = total_frames
        return f"frame_{frame_num:04d}.jpg"
    
    for start, end, text in segments_raw:
        frame_name = get_frame_at_time(start)
        idx = int(frame_name.split("_")[1].split(".")[0]) - 1
        caption = captions[idx] if idx < len(captions) else "(无描述)"
        merged += f"## [{start:.0f}s - {end:.0f}s]\n"
        merged += f"**语音**: {text}\n"
        merged += f"**画面**: {caption}\n\n"
    return merged