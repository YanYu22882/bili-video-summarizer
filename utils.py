import os
import re
import time
import requests
import torch
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（如果存在）
load_dotenv()

# ============================================================
# 路径配置（动态获取，适配任何电脑）
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WHISPER_MODEL_PATH = os.path.join(BASE_DIR, "whisper-small")
BLIP_MODEL_PATH = os.path.join(BASE_DIR, "blip-model")

# ============================================================
# API 密钥（从环境变量读取，避免硬编码）
# ============================================================
AGNES_API_KEY = os.getenv("AGNES_API_KEY", "")
if not AGNES_API_KEY:
    print("⚠️ 警告：未设置 AGNES_API_KEY 环境变量")
    print("   请在项目根目录创建 .env 文件，内容为：AGNES_API_KEY=你的密钥")

AGNES_API_URL = "https://apihub.agnes-ai.com/v1/chat/completions"
USE_API = "agnes"  # 可选 "agnes" 或 "deepseek"

# ============================================================
# 设备自动检测
# ============================================================
def resolve_device():
    if torch.cuda.is_available():
        return "cuda"
    else:
        return "cpu"

# ============================================================
# 模型加载函数
# ============================================================
def load_whisper():
    from faster_whisper import WhisperModel
    device = resolve_device()
    compute_type = "float16" if device == "cuda" else "int8"
    print(f"⏳ [Whisper] 加载模型中... (设备: {device})")
    model = WhisperModel(WHISPER_MODEL_PATH, device=device, compute_type=compute_type)
    print("✅ [Whisper] 加载完成")
    return model

def load_blip():
    from transformers import BlipProcessor, BlipForConditionalGeneration
    device = resolve_device()
    print(f"⏳ [BLIP] 加载 Processor... (设备: {device})")
    start = time.time()
    processor = BlipProcessor.from_pretrained(BLIP_MODEL_PATH)
    print(f"✅ [BLIP] Processor 加载完成，耗时 {time.time()-start:.1f}s")
    print("⏳ [BLIP] 加载 Model（~1GB，请稍候）...")
    start = time.time()
    model = BlipForConditionalGeneration.from_pretrained(BLIP_MODEL_PATH)
    print(f"✅ [BLIP] Model 加载完成，耗时 {time.time()-start:.1f}s")
    model = model.to(device)
    print(f"✅ [BLIP] 移至设备 {device}")
    return processor, model, device

# ============================================================
# API 调用
# ============================================================
def call_agnes(prompt, max_tokens=3000, retries=2):
    if USE_API == "deepseek":
        raise Exception("DeepSeek 未配置，请使用 Agnes")
    else:
        return call_agnes_api(prompt, max_tokens, retries)

def call_agnes_api(prompt, max_tokens=3000, retries=2):
    if not AGNES_API_KEY:
        raise Exception("AGNES_API_KEY 未设置，请在项目根目录创建 .env 文件")
    headers = {
        "Authorization": f"Bearer {AGNES_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "agnes-2.0-flash",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens
    }
    for attempt in range(retries + 1):
        try:
            response = requests.post(AGNES_API_URL, headers=headers, json=data, timeout=300)
            result = response.json()
            if "choices" not in result:
                error_msg = result.get("error", {}).get("message", str(result))
                raise Exception(f"API 返回异常: {error_msg}")
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            if attempt < retries:
                print(f"⏳ API 超时，正在重试 ({attempt + 1}/{retries})...")
                time.sleep(3)
                continue
            else:
                raise Exception(f"API 请求超时（已重试 {retries} 次）")
        except Exception as e:
            if attempt < retries:
                print(f"⚠️ API 错误: {e}，正在重试 ({attempt + 1}/{retries})...")
                time.sleep(3)
                continue
            else:
                raise

def extract_score(eval_text):
    match = re.search(r'评分[：:]\s*(\d+)\s*[/分]?', eval_text)
    if match:
        return int(match.group(1))
    match = re.search(r'(\d+)\s*分', eval_text)
    if match:
        return int(match.group(1))
    return 3