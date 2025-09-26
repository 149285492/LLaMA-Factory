import json
import random
import re
import zipfile
from html import unescape
from bs4 import BeautifulSoup

# ============ 配置部分 ============
# 2000个应该知道的文化常识 (快速充电百科知识丛书)_ (Z-Library).epub
# 中国人应知的国学常识大全集(超值白金版) (《中国人应_ (Z-Library).epub
# 中国文化常识2（遴选传统文化知识关键点，一本了解中国文_ (Z-Library).epub
# 中国文化常识全集（套装共3册） (干春松, 张晓芒) (Z-Library).epub
# 生活知识百科丛书（套装共4册） (唐书同) (Z-Library).epub
# 十万个为什么（第六版） 全套18本 彩色图文本 (韩启_ (Z-Library).epub
EPUB_PATH = "十万个为什么.epub"  # 输入 epub 文件路径
EPUB_PATH = "D:/holme/workspace_python/LLaMA-Factory/data/data_create/cyclopedia/十万个为什么.epub"  # 输入 epub 文件路径
CYCLOPEDIA_JSON = "cyclopedia_full.json"  # 输入文件（从epub解析出来的）
OUTPUT_JSON = "cyclopedia_sft.json"  # 输出文件




def extract_epub_paragraphs(epub_path: str, max_len=512):
    """从 epub 文件提取纯文本段落"""
    paragraphs = []
    with zipfile.ZipFile(epub_path, 'r') as z:
        candidates = [n for n in z.namelist() if n.lower().endswith(('.xhtml', '.html', '.htm', '.xml'))]
        # i=0
        for name in candidates:
            try:
                raw = z.read(name).decode('utf-8', errors='ignore')
            except Exception:
                raw = z.read(name).decode('latin-1', errors='ignore')

            # parseData(raw, paragraphs)
            parseShiWanWenData(raw, paragraphs,max_len)
            # i+=1
            # print(i)
            # if i>=20:
            #     break
    return paragraphs


def parseData(html_str, data):
    # 读取 html 文件
    soup = BeautifulSoup(html_str, "html.parser")
    # 简单策略：title3 作为问题，normaltext 作为答案
    current_question = None
    answers = []
    for p in soup.find_all("p"):
        cls = p.get("class")
        text = p.get_text(strip=True)
        if not text:
            continue
        if cls and "title3" in cls:  # 新的问题
            # 处理顿号，截取顿号后面的字符
            if "、" in text:
                text = text.split("、", 1)[1]  # 截取顿号后的部分

            # 把上一个 Q/A 存起来
            if current_question and answers:
                data.append({
                    "instruction": current_question,
                    "input": "",
                    "output": "".join(answers)
                })
            current_question = text
            answers = []
        elif cls and "normaltext" in cls:
            answers.append(text)

    # 最后一条也要保存
    if current_question and answers:
        data.append({
            "instruction": current_question,
            "input": "",
            "output": "".join(answers)
        })

    # # 保存为 jsonl
    # with open("llamafactory_dataset.jsonl", "w", encoding="utf-8") as f:
    #     for d in data:
    #         f.write(json.dumps(d, ensure_ascii=False) + "\n")



def parseShiWanWenData(html_str, data, max_len):
    # 读取 html 文件
    soup = BeautifulSoup(html_str, "html.parser")

    current_title = None
    current_content = []

    for tag in soup.find_all(["h3", "p"]):
        # 处理标题
        if tag.name == "h3" and "bodycontent-second-title" in " ".join(tag.get("class", [])):
            # 保存上一条
            if current_title and current_content:
                print(len("".join(current_content)))
                if (len("".join(current_content)) +len(current_title)) <= max_len:
                    data.append({
                        "instruction": current_title.replace("　", " "),
                        "input": "",
                        "output": "".join(current_content)
                    })
            current_title = tag.get_text(strip=True)
            current_content = []
        # 处理正文
        elif tag.name == "p" and "bodycontent-text" in " ".join(tag.get("class", [])):
            text = tag.get_text(strip=True).replace("　", " ")
            if text:
                # 过滤掉无关字段
                if text.startswith("【微博士】") or text.startswith("【微问题】") or text.startswith("【关键词】")  or text.startswith("【科学人】") or text.startswith("【实验场】"):
                    continue
                current_content.append(text)

    # 保存最后一条
    if current_title and current_content:
        if (len("".join(current_content)) + len(current_title)) <= max_len:
            data.append({
                "instruction": current_title.replace("　", " "),
                "input": "",
                "output": "".join(current_content)
            })


    # # 输出为 JSONL
    # with open("llamafactory_dataset.jsonl", "w", encoding="utf-8") as f:
    #     for d in data:
    #         f.write(json.dumps(d, ensure_ascii=False) + "\n")




def main():
    paragraphs = extract_epub_paragraphs(EPUB_PATH,512)
    print(f"提取段落数: {len(paragraphs)}")

    # 保存 JSONL
    with open(CYCLOPEDIA_JSON, "w", encoding="utf-8") as fjsonl:
        fjsonl.write(json.dumps(paragraphs, ensure_ascii=False) + "")

    print(f"已保存 JSONL 文件: {CYCLOPEDIA_JSON}")


if __name__ == "__main__":
    main()
