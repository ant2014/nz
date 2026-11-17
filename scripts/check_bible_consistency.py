#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""校验《场景锚点图方案》正文与 bible_100.json 的锁定串是否逐字一致。

用法（在项目根目录）： python scripts/check_bible_consistency.py
退出码：0 = 全部一致；1 = 有不一致项。
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MD = ROOT / "哪吒英文启蒙动画_场景锚点图方案_V1.0.md"
BIBLE = ROOT / "bible_100.json"


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def take_fence(lines, start):
    """从 start 行开始找紧随的 ``` 代码块，返回 (内容, 结束行号)。"""
    j = start
    while j < len(lines) and not lines[j].strip().startswith("```") and lines[j].strip() != "":
        j += 1
    if j >= len(lines) or not lines[j].strip().startswith("```"):
        return None, start
    j += 1
    block = []
    while j < len(lines) and not lines[j].strip().startswith("```"):
        block.append(lines[j])
        j += 1
    return " ".join(block), j


def main():
    if not (MD.exists() and BIBLE.exists()):
        print("[FAIL] 文件缺失：md=%s json=%s" % (MD.exists(), BIBLE.exists()))
        return 1

    md_text = MD.read_text(encoding="utf-8")
    try:
        bible = json.loads(BIBLE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print("[FAIL] bible_100.json 不是合法 JSON：%s" % e)
        return 1

    lines = md_text.splitlines()
    problems = []

    # ---------- 1. 场景锁 ----------
    md_scene = {}
    cur = None
    i = 0
    while i < len(lines):
        m = re.match(r"#### (S\d{2}-\d+|SKY-1)\s", lines[i])
        if m:
            cur = m.group(1)
        elif re.match(r"#### ", lines[i]):
            cur = None
        if cur and lines[i].strip() == "**LOCK**":
            block, end = take_fence(lines, i + 1)
            if block:
                md_scene[cur] = norm(block)
            i = end
        i += 1

    json_scene = {k: norm(v["lock"]) for k, v in bible.get("scenes", {}).items()}

    for k in sorted(set(json_scene) - set(md_scene)):
        problems.append("场景 %s：正文没有 LOCK 代码块" % k)
    for k in sorted(set(md_scene) - set(json_scene)):
        problems.append("场景 %s：json 没有对应条目" % k)
    for k in sorted(set(md_scene) & set(json_scene)):
        if md_scene[k] != json_scene[k]:
            problems.append(
                "场景 %s：LOCK 不一致\n    正文: %s...\n    json: %s..."
                % (k, md_scene[k][:110], json_scene[k][:110])
            )

    # ---------- 2. 角色锁（独立代码块：C01 / C01b / C01c / C08） ----------
    md_char = {}
    cur_char = None
    i = 0
    while i < len(lines):
        m = re.match(r"\*\*(C(?:01|01b|01c|08))\s", lines[i])
        if m:
            cur_char = m.group(1)
        elif lines[i].startswith("### "):
            cur_char = None
        if cur_char and lines[i].strip().startswith("```") and cur_char not in md_char:
            block, end = take_fence(lines, i)
            if block:
                md_char[cur_char] = norm(block)
            i = end
        i += 1

    json_char = {k: norm(v["lock"]) for k, v in bible.get("characters", {}).items()}
    for k in sorted(md_char):
        if k not in json_char:
            problems.append("角色 %s：json 没有对应条目" % k)
        elif md_char[k] != json_char[k]:
            problems.append(
                "角色 %s：LOCK 不一致\n    正文: %s...\n    json: %s..."
                % (k, md_char[k][:110], json_char[k][:110])
            )

    # ---------- 3. 角色锁（表格里的反引号串） ----------
    md_rows = {}
    pat_row = re.compile(r"^\| (C[0-9A-C][^|]*?) \|(?:[^|]*\|){2}\s*`([^`]+)`\s*\|", re.M)
    for code_key, lock in pat_row.findall(md_text):
        md_rows[code_key.strip()] = norm(lock)
    for k, v in sorted(md_rows.items()):
        if k not in json_char:
            problems.append("角色 %s：json 没有对应条目" % k)
        elif v != json_char[k]:
            problems.append(
                "角色 %s：LOCK 不一致\n    正文: %s...\n    json: %s..."
                % (k, v[:110], json_char[k][:110])
            )

    # ---------- 4. 数量与结构 ----------
    print("正文场景 LOCK：%d 条；json 场景：%d 条" % (len(md_scene), len(json_scene)))
    print("正文角色 LOCK：%d 条（代码块 %d + 表格 %d）；json 角色：%d 条"
          % (len(set(md_char) | set(md_rows)), len(md_char), len(md_rows), len(json_char)))
    print("json 道具：%d 件；批次：%d 批" % (len(bible.get("props", [])), len(bible.get("batches", []))))

    if len(json_scene) != 33:
        problems.append("场景条目应为 33，实为 %d" % len(json_scene))
    if len(md_scene) != 33:
        problems.append("正文场景 LOCK 应为 33，实为 %d" % len(md_scene))
    if len(json_char) != 23:
        problems.append("角色条目应为 23，实为 %d" % len(json_char))
    if len(set(md_char) | set(md_rows)) != 23:
        problems.append("正文角色 LOCK 应为 23，实为 %d" % len(set(md_char) | set(md_rows)))

    # ---------- 5. H3 块与图数总账 ----------
    h3 = bible.get("h3") or {}
    modes = h3.get("modes") or {}
    expect_counts = {"T2VA": 0, "I2VA": 1, "FL2VA": 2, "L2VA": 1}
    for m, n in expect_counts.items():
        if m not in modes:
            problems.append("h3.modes 缺少 %s" % m)
        elif modes[m].get("images") != n:
            problems.append("h3.modes.%s 图数应为 %s，实为 %s" % (m, n, modes[m].get("images")))
    if "Ref2VA" not in modes:
        problems.append("h3.modes 缺少 Ref2VA")

    # 首行指令必须在正文逐字出现（这是 H3 最容易写飘的地方）
    md_norm = norm(md_text)
    for m in ("I2VA", "FL2VA", "L2VA"):
        ins = (modes.get(m) or {}).get("instruction")
        if not ins:
            problems.append("h3.modes.%s 缺 instruction" % m)
        elif norm(ins) not in md_norm:
            problems.append("h3.modes.%s 的首行指令未在正文逐字出现" % m)

    rev = h3.get("reverse_angle_scenes") or []
    for s in rev:
        if s not in json_scene:
            problems.append("R 机位场景 %s 不在 scenes 里" % s)
    if len(rev) != 6:
        problems.append("R 机位场景应为 6 个，实为 %d" % len(rev))

    total = sum(b.get("images", 0) for b in bible.get("batches", []))
    if total != 206:
        problems.append("批次图数合计应为 206，实为 %d" % total)
    if "206 张" not in md_norm:
        problems.append("正文第七章未写出 206 张的合计")

    print("H3 模式：%d 种；R 机位场景：%d 个；批次图数合计：%d 张"
          % (len(modes), len(rev), total))

    if problems:
        print("\n[FAIL] 发现 %d 处问题：" % len(problems))
        for p in problems:
            print(" -", p)
        return 1

    print("\n[OK] 全部锁定串逐字一致。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
