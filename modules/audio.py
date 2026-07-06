import subprocess

def extract_audio(video_path, audio_path):
    """从视频中提取音频"""
    subprocess.run(
        f'ffmpeg -i "{video_path}" -vn -acodec mp3 "{audio_path}" -y',
        shell=True, capture_output=True, check=True
    )