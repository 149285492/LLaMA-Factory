import random
import zipfile
import re
import json
import uuid
import csv
from html import unescape
from pathlib import Path

# ============ 配置部分 ============
EPUB_PATH = ".\data\民间笑话.epub"  # 输入 epub 文件路径
JOKES_JSONL = "jokes_full.jsonl"  # 输入文件（从epub解析出来的）
OUTPUT_JSONL = "jokes_sft.jsonl"  # 输出文件

# =================================

def strip_tags(text: str) -> str:
    """去掉 HTML 标签并清理文本"""
    text = re.sub(r'(?is)<(script|style).*?>.*?(</\\1>)', ' ', text)
    text = re.sub(r'(?i)<br\s*/?>', '\n', text)
    text = re.sub(r'(?i)</p\s*>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\n\s+\n', '\n\n', text)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()


def extract_epub_paragraphs(epub_path: str):
    """从 epub 文件提取纯文本段落"""
    paragraphs = []
    with zipfile.ZipFile(epub_path, 'r') as z:
        candidates = [n for n in z.namelist() if n.lower().endswith(('.xhtml', '.html', '.htm', '.xml'))]
        for name in candidates:
            try:
                raw = z.read(name).decode('utf-8', errors='ignore')
            except Exception:
                raw = z.read(name).decode('latin-1', errors='ignore')
            text = strip_tags(raw)
            if not text:
                continue
            # 保留换行作为分段依据
            parts = [p.strip() for p in re.split(r'\n{2,}', text) if p.strip()]
            for p in parts:
                paragraphs.append({'source_file': name, 'paragraph': p})
    return paragraphs


def merge_paragraphs(paragraphs, max_len=1500):
    """合并连续段落为完整笑话，直到达到一定长度或遇到明显分隔"""
    jokes = []
    buffer = []
    last_file = None

    def flush():
        if buffer:
            jokes.append({
                "instruction": '讲个笑话',
                "input": '',
                "text": "\n".join(buffer).strip()
            })
            buffer.clear()

    for p in paragraphs:
        txt = p["paragraph"]
        # 跳过目录、版权、广告等无关内容
        if re.search(r'(目录|版权|出版社|编著|出版|书号)', txt):
            flush()
            continue

        # 如果换章节文件了，先清空 buffer
        if last_file is not None and p["source_file"] != last_file:
            flush()

        # 累积到 buffer
        buffer.append(txt)
        last_file = p["source_file"]

        # 如果内容过长，认为是一个完整笑话，flush
        if len("\n".join(buffer)) > max_len:
            flush()

    flush()
    return jokes


def filter_jokes(jokes, min_chars=30, max_chars=3000):
    """过滤掉过短或过长的内容"""
    out = []
    for j in jokes:
        t = j['text'].strip()
        if len(t) < min_chars or len(t) > max_chars:
            continue
        out.append(j)
    return out


INSTRUCTION_TEMPLATES = [
    "讲个笑话",
    "给我讲个笑话",
    "说一个搞笑的故事",
    "来一个短笑话",
    "讲个幽默段子",
    "来点轻松的笑话",
    "说个冷笑话",
    "给我讲一个有趣的小故事",
    "说个好玩的笑话",
]


def clean_text(text: str) -> str:
    """去掉书名和标题，只保留正文"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if not lines:
        return text.strip()

    # 如果首行是 "民间笑话" → 去掉
    if lines[0] == "民间笑话":
        lines = lines[1:]

    # 再去掉标题（通常在第二行）
    if len(lines) > 1:
        lines = lines[1:]

    return "\n".join(lines).strip()

def output_text():
    with open(JOKES_JSONL, "r", encoding="utf-8") as fin, \
            open(OUTPUT_JSONL, "w", encoding="utf-8") as fout:
        maps= []
        for line in fin:
            obj = json.loads(line)
            joke = clean_text(obj["text"])
            if not joke:
                continue

            record = {
                "instruction": random.choice(INSTRUCTION_TEMPLATES),
                "input": "",
                "text": joke
            }
            maps.append(record)
        fout.write(json.dumps(maps, ensure_ascii=False))

    print(f"已生成训练数据: {OUTPUT_JSONL}")


def main():
    paragraphs = extract_epub_paragraphs(EPUB_PATH)
    print(f"提取段落数: {len(paragraphs)}")

    jokes = merge_paragraphs(paragraphs)
    print(f"合并后笑话数: {len(jokes)}")

    jokes = filter_jokes(jokes)
    print(f"过滤后笑话数: {len(jokes)}")

    # 保存 JSONL
    with open(JOKES_JSONL, "w", encoding="utf-8") as fjsonl:
        for j in jokes:
            fjsonl.write(json.dumps(j, ensure_ascii=False) + "\n")

    print(f"已保存 JSONL 文件: {JOKES_JSONL}")

    output_text()

if __name__ == "__main__":
    main()
