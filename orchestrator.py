import os
import shutil
import time
from pathlib import Path
from datetime import datetime

from modules.audio import extract_audio
from modules.frames import extract_frames
from modules.transcribe import transcribe_audio
from modules.vision import describe_frames
from modules.fusion import fuse
from modules.summarize import generate_summary
from decision import decide_parameters
from database import add_history

def process_video_pipeline(video_path, video_name, status_holder, progress_bar, time_remaining_placeholder, cancel_flag=None,
                           whisper_model=None, blip_processor=None, blip_model=None, device=None,
                           user_prefs=None, ask_user_callback=None):
    """完整处理流水线"""
    print("🔥 进入 process_video_pipeline")
    try:
        # 自主决策
        if status_holder:
            status_holder.update(label="分析视频特征...", state="running")
        if progress_bar:
            progress_bar.progress(2)
        params = decide_parameters(video_path, user_prefs)
        target_frames = params["target_frames"]
        template = params["template"]
        enable_tools = params["enable_tools"]
        enable_deep_reflection = params["enable_deep_reflection"]
        
        if user_prefs:
            if 'enable_tools' in user_prefs:
                enable_tools = user_prefs['enable_tools']
            if 'enable_reflection' in user_prefs:
                enable_deep_reflection = user_prefs['enable_reflection']
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'bili_notes' / f"{video_name}_{timestamp}"
        work_dir.mkdir(parents=True, exist_ok=True)

        audio_path = work_dir / "audio.mp3"
        frames_dir = work_dir / "frames"
        context_path = work_dir / "full_context.txt"
        note_path = work_dir / "final_note.md"

        shutil.copy2(video_path, work_dir / f"{video_name}.mp4")

        if cancel_flag and cancel_flag():
            shutil.rmtree(work_dir, ignore_errors=True)
            if status_holder:
                status_holder.update(label="⏹️ 已取消", state="error")
            return None, None

        # 提取音频
        print("🎵 开始提取音频...")
        if status_holder:
            status_holder.update(label="提取音频...", state="running")
        if progress_bar:
            progress_bar.progress(5)
        start = time.time()
        extract_audio(video_path, audio_path)
        elapsed = time.time() - start
        print(f"✅ 音频提取完成，耗时 {elapsed:.1f}s")
        if status_holder:
            status_holder.update(label="音频提取完成 ✅", state="complete")
        if progress_bar:
            progress_bar.progress(10)
        if time_remaining_placeholder:
            remaining = elapsed * 5
            time_remaining_placeholder.info(f"⏳ 预计剩余：{int(remaining//60)}分{int(remaining%60)}秒")

        # 抽帧
        if cancel_flag and cancel_flag():
            shutil.rmtree(work_dir, ignore_errors=True)
            if status_holder:
                status_holder.update(label="⏹️ 已取消", state="error")
            return None, None
        if status_holder:
            status_holder.update(label=f"抽取关键帧（目标{target_frames}帧）...", state="running")
        if progress_bar:
            progress_bar.progress(15)
        start = time.time()
        images, fps = extract_frames(video_path, frames_dir, target_frames)
        total_frames = len(images)
        elapsed = time.time() - start
        if status_holder:
            status_holder.update(label=f"共抽取 {total_frames} 帧 ✅", state="complete")
        if progress_bar:
            progress_bar.progress(20)
        if time_remaining_placeholder:
            remaining = elapsed * 4
            time_remaining_placeholder.info(f"⏳ 预计剩余：{int(remaining//60)}分{int(remaining%60)}秒")

        # Whisper 转写
        if cancel_flag and cancel_flag():
            shutil.rmtree(work_dir, ignore_errors=True)
            if status_holder:
                status_holder.update(label="⏹️ 已取消", state="error")
            return None, None
        if status_holder:
            status_holder.update(label="语音转写中...", state="running")
        if progress_bar:
            progress_bar.progress(25)
        start = time.time()
        raw_transcript, segments_raw, info = transcribe_audio(audio_path, whisper_model)
        elapsed = time.time() - start
        if status_holder:
            status_holder.update(label="语音转写完成 ✅", state="complete")
        if progress_bar:
            progress_bar.progress(50)
        if time_remaining_placeholder:
            remaining = elapsed * 3
            time_remaining_placeholder.info(f"⏳ 预计剩余：{int(remaining//60)}分{int(remaining%60)}秒")

        # ========== 画面描述（快速模式跳过） ==========
        if cancel_flag and cancel_flag():
            shutil.rmtree(work_dir, ignore_errors=True)
            if status_holder:
                status_holder.update(label="⏹️ 已取消", state="error")
            return None, None
        if status_holder:
            status_holder.update(label=f"画面分析中（{total_frames}帧）...", state="running")
        if progress_bar:
            progress_bar.progress(55)
        start = time.time()
        fast_mode = user_prefs.get('fast_mode', False) if user_prefs else False
        if not fast_mode and blip_processor is not None and blip_model is not None:
            captions = describe_frames(images, blip_processor, blip_model, device)
        else:
            captions = ["（快速模式：跳过画面描述）"] * total_frames
            if fast_mode:
                print("⚡ 快速模式已启用，跳过 BLIP 画面描述")
            else:
                print("⚠️ BLIP 未启用，使用占位描述")
        elapsed = time.time() - start
        if status_holder:
            status_holder.update(label="画面分析完成 ✅", state="complete")
        if progress_bar:
            progress_bar.progress(85)
        if time_remaining_placeholder:
            remaining = elapsed * 1.5
            time_remaining_placeholder.info(f"⏳ 预计剩余：{int(remaining//60)}分{int(remaining%60)}秒")

        # 融合
        if cancel_flag and cancel_flag():
            shutil.rmtree(work_dir, ignore_errors=True)
            if status_holder:
                status_holder.update(label="⏹️ 已取消", state="error")
            return None, None
        if status_holder:
            status_holder.update(label="融合音频与画面...", state="running")
        if progress_bar:
            progress_bar.progress(90)
        start = time.time()
        context = fuse(segments_raw, captions, fps, total_frames)
        with open(context_path, "w", encoding="utf-8") as f:
            f.write(context)
        elapsed = time.time() - start
        if status_holder:
            status_holder.update(label="融合完成 ✅", state="complete")
        if progress_bar:
            progress_bar.progress(92)

        # 总结
        if cancel_flag and cancel_flag():
            shutil.rmtree(work_dir, ignore_errors=True)
            if status_holder:
                status_holder.update(label="⏹️ 已取消", state="error")
            return None, None
        if status_holder:
            status_holder.update(label="生成总结笔记...", state="running")
        if progress_bar:
            progress_bar.progress(95)
        start = time.time()

        custom_prompt = user_prefs.get('custom_prompt', "") if user_prefs else ""
        note = generate_summary(context, template, custom_prompt, enable_tools, enable_deep_reflection)

        with open(note_path, "w", encoding="utf-8") as f:
            f.write(note)
        elapsed = time.time() - start
        if status_holder:
            status_holder.update(label="笔记生成完成 ✅", state="complete")
        if progress_bar:
            progress_bar.progress(100)
        if time_remaining_placeholder:
            time_remaining_placeholder.success("✅ 全部完成！")

        add_history(video_name, note[:200] + "...", template, custom_prompt)

        return note, work_dir

    except Exception as e:
        if 'work_dir' in locals() and work_dir and work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        if status_holder:
            status_holder.update(label=f"❌ 错误: {str(e)[:200]}", state="error")
        print(f"❌ orchestrator 异常: {e}")
        return None, None