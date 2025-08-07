#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filter_m3u.py
执行顺序：
1. 先挑出 group-title="主力-央视"/"主力-卫视"/"主力-其他" 三个组
2. 央视组内删除 4 条标清流
3. CCTV-5+HD 紧跟 CCTV-5HD
4. 统一 CCTV13/14/15 的 id/name/显示名
5. 最后：去掉 group-title 里的 "主力-" 前缀 及 频道名末尾的 "-主力"
"""

import re
import sys
import requests

SRC_URL = "https://sub.ottiptv.cc/iptv.m3u"  # 换成你的源
OUTPUT  = "live.m3u"

# 允许的分组（先保留完整前缀，第5步再统一去掉）
KEEP_GROUPS = {"主力-央视", "主力-卫视", "主力-其他"}
# 央视组内需要删除的频道名（原始名）
DELETE_NAMES = {"CCTV-3-主力", "CCTV-5-主力", "CCTV-6-主力", "CCTV-8-主力"}

# 央视频道映射：原始显示名 -> (新显示名, 新tvg-id, 新tvg-name)
CCTV_RENAME = {
    "CCTV-新闻HD-主力": ("CCTV-13HD", "CCTV13", "CCTV13"),
    "CCTV-少儿HD-主力": ("CCTV-14HD", "CCTV14", "CCTV14"),
    "CCTV-音乐HD-主力": ("CCTV-15HD", "CCTV15", "CCTV15"),
}

# ---------- 工具 ----------
def parse_m3u(text: str):
    items, buf = [], []
    for ln in text.splitlines():
        ln = ln.strip()
        if ln.startswith("#EXTINF"):
            if buf: buf.clear()
            buf.append(ln)
        elif ln and not ln.startswith("#"):
            buf.append(ln)
            if len(buf) == 2:
                items.append(tuple(buf))
                buf.clear()
    return items

def group_of(extinf: str) -> str:
    m = re.search(r'group-title="([^"]*)"', extinf)
    return m.group(1) if m else ""

def channel_name(extinf: str) -> str:
    return extinf.split(",")[-1].strip()

def fix_extinf(extinf: str, new_name: str, new_id: str = None, new_name_attr: str = None) -> str:
    extinf = re.sub(r"(#EXTINF:.*,).*$", r"\1" + new_name, extinf)
    if new_id:
        extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{new_id}"', extinf)
    if new_name_attr:
        extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{new_name_attr}"', extinf)
    return extinf

# ---------- 主流程 ----------
def main():
    try:
        raw = requests.get(SRC_URL, timeout=30).text
    except Exception as e:
        print("下载失败:", e)
        sys.exit(1)

    items = parse_m3u(raw)

    # 1️⃣ 先挑出三个组
    filtered = [
        (extinf, url) for extinf, url in items
        if group_of(extinf) in KEEP_GROUPS
    ]

    # 2️⃣ 拆分央视组
    cctv_items  = [t for t in filtered if group_of(t[0]) == "主力-央视"]
    other_items = [t for t in filtered if group_of(t[0]) != "主力-央视"]

    # 3️⃣ 央视组内删除 4 条标清流
    cctv_items = [
        (extinf, url) for extinf, url in cctv_items
        if channel_name(extinf) not in DELETE_NAMES
    ]

    # 4️⃣ 统一 CCTV13/14/15 的显示名、id、name
    processed = []
    for extinf, url in cctv_items:
        name = channel_name(extinf)
        if name in CCTV_RENAME:
            new_name, new_id, new_name_attr = CCTV_RENAME[name]
            extinf = fix_extinf(extinf, new_name, new_id, new_name_attr)
        processed.append((extinf, url))

    # 5️⃣ CCTV-5+HD 紧跟 CCTV-5HD
    idx5 = idx5p = None
    for i, (e, _) in enumerate(processed):
        n = channel_name(e)
        if n == "CCTV-5HD-主力":
            idx5 = i
        elif n == "CCTV-5+HD-主力":
            idx5p = i
    if idx5 is not None and idx5p is not None:
        item5p = processed.pop(idx5p)
        insert = idx5 + 1 if idx5p > idx5 else idx5
        processed.insert(insert, item5p)

    # 6️⃣ 合并
    final = processed + other_items

    # 7️⃣ 最后统一清理：
    #   - 去掉 group-title 里的 "主力-"
    #   - 去掉频道名末尾的 "-主力"
    cleaned = []
    for extinf, url in final:
        # 去掉 group-title 里的 "主力-"
        extinf = re.sub(r'group-title="主力-(.*?)"', r'group-title="\1"', extinf)
        # 去掉频道名末尾的 "-主力"
        extinf = re.sub(r'(#EXTINF:.*,.*)-主力$', r'\1', extinf)
        cleaned.append((extinf, url))

    # 8️⃣ 写出
    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in cleaned:
            f.write(extinf + "\n")
            f.write(url + "\n")

    print("已生成", OUTPUT, "共", len(cleaned), "条频道")

if __name__ == "__main__":
    main()
