#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
filter_m3u.py
1. 仅保留 group-title="主力-央视"/"主力-卫视"/"主力-其他"
2. 央视组内删除 4 条标清流
3. 把 CCTV-5+HD-主力 移动到 CCTV-5HD-主力 之后
4. 重命名 CCTV-新闻HD-主力 / 少儿HD-主力 / 音乐HD-主力
"""

import re
import sys
import requests

SRC_URL = "https://sub.ottiptv.cc/iptv.m3u"   # 换成你的源
OUTPUT  = "live.m3u"

KEEP_GROUPS = {"主力-央视", "主力-卫视", "主力-其他"}
DELETE_NAMES = {"CCTV-3-主力", "CCTV-5-主力", "CCTV-6-主力", "CCTV-8-主力"}
RENAME_MAP = {
    "CCTV-新闻HD-主力": "CCTV-13HD-主力",
    "CCTV-少儿HD-主力": "CCTV-14HD-主力",
    "CCTV-音乐HD-主力": "CCTV-15HD-主力",
}

def parse_m3u(text: str):
    lines = [ln.strip() for ln in text.splitlines()]
    items, buf = [], []
    for ln in lines:
        if ln.startswith("#EXTINF"):
            if buf:            # 上一条没有 url，丢弃
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

def set_channel_name(extinf: str, new_name: str) -> str:
    return re.sub(r"(#EXTINF:.*,).*$", r"\1" + new_name, extinf)

def reorder_and_rename_cctv(items):
    """对央视组：重命名+调整顺序"""
    # 先把名字改掉
    renamed = []
    for extinf, url in items:
        name = channel_name(extinf)
        if name in RENAME_MAP:
            extinf = set_channel_name(extinf, RENAME_MAP[name])
        renamed.append((extinf, url))

    # 再调整顺序：把 CCTV-5+HD-主力 移到 CCTV-5HD-主力 后
    idx_5 = idx_5p = None
    for i, (extinf, _) in enumerate(renamed):
        if channel_name(extinf) == "CCTV-5HD-主力":
            idx_5 = i
        elif channel_name(extinf) == "CCTV-5+HD-主力":
            idx_5p = i

    if idx_5 is not None and idx_5p is not None:
        item_5p = renamed.pop(idx_5p)
        insert_pos = idx_5 + 1 if idx_5p > idx_5 else idx_5
        renamed.insert(insert_pos, item_5p)

    return renamed

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

    # 拆分
    cctv_items  = [t for t in filtered if group_of(t[0]) == "主力-央视"]
    other_items = [t for t in filtered if group_of(t[0]) != "主力-央视"]

    # 央视内部重命名+排序
    cctv_items = reorder_and_rename_cctv(cctv_items)

    # 合并
    final = cctv_items + other_items

    with open(OUTPUT, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for extinf, url in final:
            f.write(extinf + "\n")
            f.write(url + "\n")

    print("已生成", OUTPUT, "共", len(final), "条频道")

if __name__ == "__main__":
    main()