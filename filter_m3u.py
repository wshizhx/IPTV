#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filter_m3u.py
1. 仅保留 主力-央视 / 主力-卫视 / 主力-其他
2. 央视组内删除 4 条标清流
3. 把 CCTV-5+HD-主力 移动到 CCTV-5HD-主力 之后
4. 重命名频道显示名
5. 统一 tvg-id / tvg-name 为 CCTV13 / CCTV14 / CCTV15
"""

import re
import sys
import requests

SRC_URL = "https://sub.ottiptv.cc/iptv.m3u"  # 换成你的源
OUTPUT  = "live.m3u"

KEEP_GROUPS = {"主力-央视", "主力-卫视", "主力-其他"}
DELETE_NAMES  = {"CCTV-3-主力", "CCTV-5-主力", "CCTV-6-主力", "CCTV-8-主力"}

# 频道名映射
RENAME_MAP = {
    "CCTV-新闻HD-主力": "CCTV-13HD-主力",
    "CCTV-少儿HD-主力": "CCTV-14HD-主力",
    "CCTV-音乐HD-主力": "CCTV-15HD-主力"
}

# tvg-id / tvg-name 映射
ID_NAME_FIX = {
    "CCTV-新闻HD-主力": ("CCTV13", "CCTV13"),
    "CCTV-少儿HD-主力": ("CCTV14", "CCTV14"),
    "CCTV-音乐HD-主力": ("CCTV15", "CCTV15")
}

# ---------- 通用工具 ----------
def parse_m3u(text: str):
    lines = [ln.strip() for ln in text.splitlines()]
    items, buf = [], []
    for ln in lines:
        if ln.startswith("#EXTINF"):
            if buf:
                buf.clear()
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

def fix_extinf(extinf: str, new_name: str, new_id: str, new_name_attr: str) -> str:
    # 替换频道显示名
    extinf = re.sub(r'(#EXTINF:.*,).*$', r'\1' + new_name, extinf)
    # 替换 tvg-id 和 tvg-name
    extinf = re.sub(r'tvg-id="[^"]*"', f'tvg-id="{new_id}"', extinf)
    extinf = re.sub(r'tvg-name="[^"]*"', f'tvg-name="{new_name_attr}"', extinf)
    return extinf

# ---------- 主流程 ----------
def main():
    try:
        raw = requests.get(SRC_URL, timeout=30).text
    except Exception as e:
        print("下载源失败:", e, file=sys.stderr)
        sys.exit(1)

    items = parse_m3u(raw)
    filtered = []

    for extinf, url in items:
        grp = group_of(extinf)
        if grp not in KEEP_GROUPS:
            continue
        name = channel_name(extinf)
        if grp == "主力-央视" and name in DELETE_NAMES:
            continue
        filtered.append((extinf, url))

    # 央视单独处理
    cctv_items  = [t for t in filtered if group_of(t[0]) == "主力-央视"]
    other_items = [t for t in filtered if group_of(t[0]) != "主力-央视"]

    # 重命名+改ID+改NAME
    processed = []
    for extinf, url in cctv_items:
        name = channel_name(extinf)
        if name in RENAME_MAP:
            new_name = RENAME_MAP[name]
            new_id, new_name_attr = ID_NAME_FIX[name]
            extinf = fix_extinf(extinf, new_name, new_id, new_name_attr)
        processed.append((extinf, url))

    # 调整顺序：CCTV-5+HD-主力 紧跟 CCTV-5HD-主力
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

    # 合并
    final = processed + other_items

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in final:
            f.write(extinf + "\n")
            f.write(url + "\n")

    print("已生成", OUTPUT, "共", len(final), "条频道")

if __name__ == "__main__":
    main()
