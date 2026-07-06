from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import subprocess
import shutil
import sqlite3
from pathlib import Path
from orchestrator import process_video_pipeline
from modules.summarize import generate_summary
from utils import load_whisper, load_blip, resolve_device, BASE_DIR
from database import get_all_history, add_history, delete_history_by_id, delete_history_by_work_dir
from bilibili_api import video, sync

# ==================== 路径配置 ====================
BBDOWN_PATH = os.path.join(BASE_DIR, "BBDown.exe")
USER_DATA_DIR = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')) / 'bili_notes'
USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="B站视频总结后端")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== 加载模型 ====================
print("⏳ 加载模型...")
whisper_model = load_whisper()
blip_processor, blip_model, device = load_blip()
print("✅ 模型加载完成")

# ==================== 接口 1：获取分P列表 ====================
@app.get("/video_info")
def get_video_info(bvid: str):
    bvid = bvid.strip()
    if not bvid.startswith("BV"):
        bvid = "BV" + bvid
    try:
        v = video.Video(bvid=bvid)
        info = sync(v.get_info())
        pages = info.get("pages", [])
        if not pages:
            pages = [{"page": 1, "part": info.get("title", "视频"), "duration": 0}]
        parts = [{"index": p.get("page"), "title": p.get("part", f"P{p.get('page')}"), "duration": p.get("duration", 0)} for p in pages]
        return {"status": "success", "parts": parts}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取失败: {str(e)}")

# ==================== 接口 2：下载分P ====================
class DownloadRequest(BaseModel):
    bvid: str
    parts: list[int]

@app.post("/download")
def download_parts(req: DownloadRequest):
    bvid = req.bvid.strip()
    if not bvid.startswith("BV"):
        bvid = "BV" + bvid
    if not os.path.exists(BBDOWN_PATH):
        raise HTTPException(status_code=500, detail="BBDown.exe 未找到")
    
    download_dir = USER_DATA_DIR / "downloads" / bvid
    download_dir.mkdir(parents=True, exist_ok=True)
    parts_str = ",".join(map(str, req.parts))
    cmd = f'"{BBDOWN_PATH}" {bvid} -p {parts_str}'
    
    try:
        os.chdir(download_dir)
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=600)
        if process.returncode != 0:
            raise Exception(process.stderr[:200])
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="下载超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")
    
    downloaded = []
    for p in req.parts:
        candidates = list(download_dir.glob(f"**/*P{p}*.mp4")) + list(download_dir.glob(f"**/*P{p}*.mkv"))
        if candidates:
            downloaded.append(str(candidates[0].resolve()))
    if not downloaded:
        all_videos = list(download_dir.glob("**/*.mp4")) + list(download_dir.glob("**/*.mkv"))
        if all_videos:
            downloaded = [str(v.resolve()) for v in all_videos]
        else:
            raise HTTPException(status_code=500, detail="下载完成但未找到视频文件")
    return {"status": "success", "video_paths": downloaded}

# ==================== 接口 3：处理视频（解析生成笔记） ====================
class ProcessRequest(BaseModel):
    video_paths: list[str]
    bvid: str = "local"
    template: str = "通用"
    enable_reflection: bool = True
    enable_tools: bool = True
    custom_prompt: str = ""
    fast_mode: bool = False  # 新增快速模式

@app.post("/process")
def process_videos(req: ProcessRequest):
    results = {}
    user_prefs = {
        "template": req.template,
        "enable_reflection": req.enable_reflection,
        "enable_tools": req.enable_tools,
        "custom_prompt": req.custom_prompt,
        "fast_mode": req.fast_mode
    }
    for path in req.video_paths:
        if not os.path.exists(path):
            results[path] = {"status": "error", "note": "文件不存在"}
            continue
        try:
            note, work_dir = process_video_pipeline(
                video_path=path,
                video_name=os.path.basename(path),
                status_holder=None,
                progress_bar=None,
                time_remaining_placeholder=None,
                cancel_flag=lambda: False,
                whisper_model=whisper_model,
                blip_processor=blip_processor,
                blip_model=blip_model,
                device=device,
                user_prefs=user_prefs,
                ask_user_callback=None
            )
            add_history(os.path.basename(path), note[:200] + "...", req.template, req.custom_prompt, work_dir=str(work_dir))
            results[path] = {"status": "success", "note": note, "work_dir": str(work_dir)}
        except Exception as e:
            results[path] = {"status": "error", "note": str(e)}
    return {"results": results}

# ==================== 接口 4：多轮对话 ====================
class ChatRequest(BaseModel):
    context: str
    current_note: str
    user_feedback: str
    template: str = "通用"
    custom_prompt: str = ""
    enable_tools: bool = True
    enable_reflection: bool = True

@app.post("/chat")
def chat_with_note(req: ChatRequest):
    full_prompt = req.template
    if req.custom_prompt:
        full_prompt += "\n" + req.custom_prompt
    if req.user_feedback:
        full_prompt += "\n用户补充意见：" + req.user_feedback
    
    new_note = generate_summary(
        context=req.context,
        template=full_prompt,
        custom_prompt="",
        enable_tools=req.enable_tools,
        enable_deep_reflection=req.enable_reflection
    )
    return {"new_note": new_note}

# ==================== 接口 5：删除笔记（使用 id） ====================
class DeleteRequest(BaseModel):
    id: int
    delete_video: bool = False

@app.post("/delete_note")
def delete_note(req: DeleteRequest):
    with sqlite3.connect("memory.db") as conn:
        c = conn.cursor()
        c.execute("SELECT work_dir FROM history WHERE id = ?", (req.id,))
        row = c.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="记录不存在")
    work_dir = row[0]
    
    if work_dir and os.path.exists(work_dir):
        work_dir_path = Path(work_dir)
        if req.delete_video:
            for ext in [".mp4", ".mkv", ".flv", ".avi", ".mov"]:
                for vf in work_dir_path.glob(f"*{ext}"):
                    try:
                        vf.unlink()
                        print(f"🗑️ 已删除视频: {vf.name}")
                    except Exception as e:
                        print(f"⚠️ 删除视频失败 {vf.name}: {e}")
        try:
            shutil.rmtree(work_dir_path)
            print(f"🗑️ 已删除笔记目录: {work_dir_path}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"删除笔记目录失败: {str(e)}")
    else:
        print(f"⚠️ work_dir 不存在或为空，只删除数据库记录")
    
    delete_history_by_id(req.id)
    return {"status": "success", "message": "已删除"}

# ==================== 接口 6：获取历史记录 ====================
@app.get("/history")
def get_history():
    records = get_all_history()
    return {"history": records}

# ==================== 接口 7：清理无效/重复记录 ====================
@app.get("/cleanup")
def cleanup_database():
    records = get_all_history()
    deleted_count = 0
    kept_work_dirs = set()
    for r in records:
        record_id = r.get("id")
        work_dir = r.get("work_dir")
        if not work_dir or "downloads" in work_dir:
            delete_history_by_id(record_id)
            deleted_count += 1
            continue
        if not os.path.exists(work_dir):
            delete_history_by_id(record_id)
            deleted_count += 1
            continue
        if not os.path.exists(os.path.join(work_dir, "final_note.md")):
            delete_history_by_id(record_id)
            deleted_count += 1
            continue
        if work_dir in kept_work_dirs:
            delete_history_by_id(record_id)
            deleted_count += 1
        else:
            kept_work_dirs.add(work_dir)
    remaining = get_all_history()
    return {
        "deleted": deleted_count,
        "remaining": len(remaining),
        "message": "清理完成！请刷新前端页面查看历史记录。"
    }

# ==================== 接口 8：健康检查 ====================
@app.get("/")
def root():
    return {"status": "ok", "message": "B站视频总结服务运行中"}