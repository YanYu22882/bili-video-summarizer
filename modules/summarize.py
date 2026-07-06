import sys
sys.path.append('..')
from utils import call_agnes, extract_score
from database import get_entity_cache, set_entity_cache
import re
import requests

def query_wikipedia(entity):
    cached = get_entity_cache(entity)
    if cached:
        return cached
    search_url = "https://zh.wikipedia.org/w/api.php"
    try:
        resp = requests.get(search_url, params={
            "action": "query",
            "list": "search",
            "srsearch": entity,
            "format": "json",
            "srlimit": 1
        }, timeout=5)
        data = resp.json()
        if not data["query"]["search"]:
            return None
        title = data["query"]["search"][0]["title"]
        resp2 = requests.get(search_url, params={
            "action": "query",
            "prop": "extracts",
            "exintro": True,
            "explaintext": True,
            "titles": title,
            "format": "json"
        }, timeout=5)
        data2 = resp2.json()
        page = next(iter(data2["query"]["pages"].values()))
        extract = page.get("extract", "")
        if extract:
            set_entity_cache(entity, extract[:500])
            return extract[:500]
    except:
        pass
    return None

def generate_summary(context, template, custom_prompt, enable_tools=True, enable_deep_reflection=True, max_retries=3):
    """生成总结（纯文本格式，无 Markdown 符号）"""
    tool_context = ""
    if enable_tools:
        entities = re.findall(r'[\u4e00-\u9fa5]{2,4}', context)
        common_words = {"这个","那个","什么","怎么","然后","就是","一个","我们","你们","他们","自己","因为","所以","但是","如果","可以","应该","需要","能够","已经","现在","时候","还是","由于","因此","对于","以下","以上","画面","视频","描述","解读","背景","知识","没有","不是","已经","之后","之前","当时","还有","以及","等等","大家","各位"}
        unique_entities = list(set([e for e in entities if e not in common_words and len(e) >= 2]))[:5]
        for ent in unique_entities:
            info = query_wikipedia(ent)
            if info:
                tool_context += f"\n【{ent}】背景知识：{info}\n"

    base_prompt = template if not custom_prompt else custom_prompt
    if tool_context:
        base_prompt += f"\n\n额外背景知识：{tool_context}"

    prompt = f"""{base_prompt}

视频内容如下：
{context}

请用纯文本格式输出笔记，不要使用任何 Markdown 或特殊符号（如 * # > _ 等）。要求如下：
1. 用空行分隔不同章节
2. 每个章节的第一行用【】括起来的标题，例如【核心概念】、【关键知识点】
3. 要点用 - 开头（但只是普通文本，不是列表符号）
4. 重要术语用双引号 " " 括起来
5. 不要使用任何星号、井号、下划线等格式标记

示例格式：
【核心概念】
这里写核心概念的内容，多个要点可以换行写。

【关键知识点】
这里写关键知识点，不同知识点之间空行分隔。

现在请生成这样的纯文本笔记："""

    note = call_agnes(prompt, max_tokens=4000)

    for attempt in range(max_retries):
        eval_prompt = f"""
你是严格的内容审核员。评估以下笔记质量，重点关注：
1. 人物是否混淆
2. 事实是否准确
3. 结构是否清晰
4. 音画关系是否正确
5. 是否包含任何 Markdown 特殊符号（如 *, #, >, _ 等），如果有则指出并要求去掉

笔记：
{note}

输出格式：
评分：X/5
问题列表：
修正建议：
"""
        eval_result = call_agnes(eval_prompt, max_tokens=500)
        score = extract_score(eval_result)
        if score >= 4.5:
            break
        correction_prompt = f"""
根据以下反馈修正笔记，确保完全去除任何 Markdown 标记符号，只保留纯文本和中文标点：

反馈：
{eval_result}

原笔记：
{note}

只输出修正后的笔记，不要添加额外说明。
"""
        note = call_agnes(correction_prompt, max_tokens=4000)

    return note