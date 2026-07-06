import subprocess

def decide_parameters(video_path, user_prefs=None):
    """自主决策：抽帧频率、模板、反思开关等"""
    probe = subprocess.run(
        f'ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "{video_path}"',
        shell=True, capture_output=True, text=True
    )
    duration = float(probe.stdout.strip()) if probe.stdout.strip() else 300
    
    # ========== 优化：大幅降低目标帧数 ==========
    if duration < 60:
        target_frames = 15
    elif duration < 300:
        target_frames = 30
    elif duration < 600:
        target_frames = 50
    else:
        target_frames = 70
    
    # 用户偏好覆盖
    if user_prefs and user_prefs.get('target_frames'):
        target_frames = user_prefs['target_frames']
    
    # 模板决策
    if "课程" in video_path or "教学" in video_path:
        template = "课程笔记"
    elif "会议" in video_path or "纪要" in video_path:
        template = "会议纪要"
    elif "科普" in video_path:
        template = "科普解读"
    else:
        template = "通用"
    
    if user_prefs and user_prefs.get('template'):
        template = user_prefs['template']
    
    # 反思和工具由前端控制，这里只取用户偏好（若无则默认False/True）
    enable_deep_reflection = user_prefs.get('enable_reflection', False) if user_prefs else False
    enable_tools = user_prefs.get('enable_tools', True) if user_prefs else True
    
    return {
        "target_frames": target_frames,
        "template": template,
        "enable_deep_reflection": enable_deep_reflection,
        "enable_tools": enable_tools,
        "duration": duration
    }