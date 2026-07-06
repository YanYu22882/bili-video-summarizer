import subprocess
from pathlib import Path

def extract_frames(video_path, frames_dir, target_frames=120):
    """动态抽帧"""
    frames_dir.mkdir(exist_ok=True)
    
    # 获取视频时长
    probe = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"',
        shell=True, capture_output=True, text=True
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 300
    fps = max(0.2, min(1.0, target_frames / duration))
    
    # 抽帧命令 - 输出路径用双引号包裹
    subprocess.run(
        f'ffmpeg -i "{video_path}" -vf "fps={fps}" "{frames_dir}/frame_%04d.jpg" -y',
        shell=True, capture_output=True, check=True
    )
    
    images = sorted(frames_dir.glob("*.jpg"), key=lambda x: int(x.stem.split("_")[1]))
    return images, fps