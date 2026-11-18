# -*- coding: utf-8 -*-
"""
通用分镜生成器（不含任何剧集内容）。

一次运行，从「每集一份配置」生成提交给 freevideo 的产物：
  video_config.json          —— 每段带生成方式（I2VA / FL2VA）、首帧 / 尾帧文件名与 H3 提示词
  05_关键帧清单_EP01.json     —— 出图用：镜号 / 方式 / A·B 文件名 / 中英提示词
  加 --with-table 时另出 03_分镜表_EP01.csv（13 列全中文大表）

生成方式
  i2va   只出首帧，H3 从首帧往前推（静态或轻运动镜头）
  fl2va  首帧 + 尾帧都出，H3 在两帧之间插值（有明确终点状态的动作镜头）

结构与产物集中在 storyboard/ 一个目录：
  storyboard/locks.json     全项目共用：STYLE / NEGATIVE / 场景 / 角色 / 光线 / 音乐 / 说话人
  storyboard/ep01.json      每集一份：集号、标题、路径、参考图、41 个镜头

用法
  python storyboard_gen.py 01                 # 写本集 video_config.json 与关键帧清单
  python storyboard_gen.py 01 --with-table    # 另出 13 列全中文分镜大表
  python storyboard_gen.py 01 --audit         # 只体检，不写文件

要做第 2 集：把 ep01.json 复制成 ep02.json，改 ep / title / out_dir / project_name /
reference_images 与 shots。新场景、新角色、新光态、新说话人加进 locks.json；
只在本集出现的写进集配置的 local 节，不要在锁文件里重复写。
"""
import argparse
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
LOCKS_PATH = os.path.join(ROOT, "storyboard", "locks.json")
EP_DIR = os.path.join(ROOT, "storyboard")

CSV_HEADER = ["镜号", "生成方式", "时长(秒)", "场景", "画面内容", "台词/旁白", "运镜", "光线",
              "首帧图提示词（中文）", "尾帧图提示词（中文）", "视频提示词（H3·中文）", "音效", "音乐"]

MODE_CN = {"i2va": "首帧推演 I2VA", "fl2va": "首尾帧 FL2VA"}
CN_NEG_TAIL = "画面不出现任何文字字幕或招牌字、不加现代物件、不做写实皮肤与三维渲染、不出现设定外的人物。"

VO_TAIL = "while every on-screen character's lips stay completely closed and no jaw moves."
LIP_TAIL = ("and the speaker's lips and jaw move in exact sync with every syllable of the line, "
            "the mouth closing fully on the final sound and the jaw settling afterwards.")
OFF_TAIL = "No on-screen character speaks, and all on-screen mouths stay completely closed."

I2VA_HEAD = ("For the target video, at 0.00 seconds into the target video, "
             "<Picture 1> (from [Shot 1]) is fully referenced.")
FL2VA_HEAD = ("How the reference pictures align with the target video — Picture 1 (from [Shot 1]) "
              "aligns with the 0.00-second mark of the target video; "
              "Picture 2 (from [Shot 1]) aligns with the {:.2f}-second mark of the target video.")

I2VA_ANCHOR = ("The video begins exactly on the composition, subject size, camera height, "
               "lens and lighting of Picture 1 and develops forward from that frame without "
               "reframing away from it.")
FL2VA_ANCHOR = ("The shot begins exactly on the composition, subject size, camera height, lens and "
                "lighting of Picture 1, develops through the action below, and lands exactly on the "
                "composition, subject size, camera height, lens and lighting of Picture 2 at the end "
                "of the shot.")


# ----------------------------------------------------------------- 锁串渲染
def render_dlg(dlg, speakers):
    """把 {spk,line,voice?,mode?} 拼成符合 H3 规范的说话人串。"""
    if not dlg:
        return ("none — no speech in this shot; all on-screen mouths stay completely closed "
                "and no jaw moves.")
    spk = dlg["spk"]
    base = speakers.get(spk, {})
    who = dlg.get("who") or base.get("who", "")
    voice = dlg.get("voice") or base.get("voice", "")
    line = dlg["line"]
    mode = dlg.get("mode") or base.get("mode", "sync")

    if mode == "offscreen":
        return ("%s (%s), off-screen behind the camera, gives one short startled cry: "
                "<d>[Chinese] %s</d> %s" % (who, spk, line, OFF_TAIL))
    if mode == "sync":
        return "%s (%s), %s, says: <d>[Chinese] %s</d> %s" % (who, spk, voice, line, LIP_TAIL)
    return ("%s (%s), %s, says in an off-screen voiceover: <d>[Chinese] %s</d> %s"
            % (who, spk, voice, line, VO_TAIL))


def merge_local(L, loc):
    """把本集专属的锁串并入全局字典。"""
    if not loc:
        return L
    out = dict(L)
    for sec in ("settings", "characters", "lights", "music", "speakers"):
        if loc.get(sec):
            merged = dict(L.get(sec, {}))
            merged.update(loc[sec])
            out[sec] = merged
    return out


# ----------------------------------------------------------------- 提示词
def frames_of(ep, idx):
    """一镜的首尾帧文件名。"""
    nn = str(ep["ep"]).zfill(2)
    a = "EP%s_S%02d_A.png" % (nn, idx)
    b = "EP%s_S%02d_B.png" % (nn, idx)
    return a, b


def build_prompt(s, L, ep, idx, mode):
    """一段 H3 提示词：首行图片对齐指令 + 三字段；字段内按「风格/场景/人物/动作/镜头/光/台词/负面」分行。"""
    chs = [L["characters"][k]["en"] for k in s["chars"]]
    chars_txt = (("CHARACTER LOCK: " + "; ".join(chs).rstrip(". ") + ".") if chs
                 else "CHARACTER LOCK: none, no figure in this shot.")

    blocks = [
        "[Shot 1] " + L["style_en"],
        "SETTING LOCK (identical in every shot of scene %s): %s"
        % (s["scene"], L["settings"][s["scene"]]["en"].rstrip(" .") + "."),
        chars_txt,
        "ACTION: " + s["action"],
        "CAMERA: " + s["camera"],
        "LIGHTING: " + L["lights"][s["light"]]["en"].rstrip(". ") + ".",
        "DIALOGUE: " + render_dlg(s.get("dlg"), L["speakers"]),
        L["negative_en"],
    ]

    if mode == "fl2va":
        head = FL2VA_HEAD.format(s["dur"])
        anchor = FL2VA_ANCHOR
    else:
        head = I2VA_HEAD
        anchor = I2VA_ANCHOR

    body = ("integrated_multimodal_description: " + blocks[0] + "\n\n" + anchor
            + "\n\n" + "\n\n".join(blocks[1:])
            + "\n\noverall_soundscape: " + s["sfx"]
            + "\n\nnon_diegetic_music: " + L["music"][s["music"]])

    return head + "\n\n" + body


def build_cn_video(s, L):
    """CSV 的「视频提示词」列：中文，人审用，不投喂。"""
    dlg = s.get("dlg")
    if dlg:
        spk = dlg["spk"]
        who = L["speakers"].get(spk, {}).get("who", spk)
        line_txt = "台词：%s 说「%s」，口型与每个字对得上，说完嘴唇闭合。" % (who, dlg["line"])
    else:
        line_txt = "本镜无人说话，所有在场人物嘴唇全程闭合。"
    return ("二维平涂动画风格。%s 镜头：%s 光线：%s %s 画面不出现任何文字。"
            % (s.get("cn_action", s["visual"]).rstrip("。"),
               s["cn_cam"].rstrip("。"),
               L["lights"][s["light"]]["cn"].rstrip("。"),
               line_txt))


# ----------------------------------------------------------------- 统计
def timecodes(shots):
    t, out = 0, []
    for s in shots:
        out.append("%d:%02d–%d:%02d" % (t // 60, t % 60,
                                        (t + s["dur"]) // 60, (t + s["dur"]) % 60))
        t += s["dur"]
    return out, t


def ratio(shots):
    """英文占比 = 英词数 /(英词数 + 中文字数/1.5)，口径同大纲 §1.6。"""
    text = " ".join(s["line"] for s in shots)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z']+", text))
    denom = en + cjk / 1.5
    return en, cjk, (en / denom if denom else 0.0)


def plan_ratio(cum_words):
    """大纲 V3.0 §1.6：MIN(0.45, 0.19 + 0.0012 × ROUND(累计新学词 × 0.7))。"""
    if cum_words is None:
        return None, None
    usable = int(round(cum_words * 0.7))
    return min(0.45, 0.19 + 0.0012 * usable), usable


def audit(shots, ep, total):
    """节奏 + 首尾帧合规体检。"""
    i2 = [s for s in shots if s.get("mode", "i2va") == "i2va"]
    fl = [s for s in shots if s.get("mode") == "fl2va"]
    imgs = len(i2) + 2 * len(fl)
    no_cast = [s for s in shots if not s["chars"]]
    no_lines = [s for s in shots if not s.get("dlg")]
    sec_no_cast = sum(s["dur"] for s in no_cast)
    sec_no_lines = sum(s["dur"] for s in no_lines)
    longest = max(shots, key=lambda s: s["dur"])
    text = " ".join(s["line"] for s in shots)
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))

    print("\n【硬指标】")
    print("  %d 镜 ｜ 合计 %d 秒 ｜ 单镜 %d–%d 秒 ｜ 平均 %.1f 秒"
          % (len(shots), total, min(s["dur"] for s in shots),
             max(s["dur"] for s in shots), total / len(shots)))
    print("  最长 %d 秒（%s）" % (longest["dur"], longest["seg"]))
    bad = [s["seg"] for s in shots if not 4 <= s["dur"] <= 15]
    print("  超 H3 时长区间：" + ("无" if not bad else ", ".join(bad)))

    print("\n【生成方式】")
    print("  I2VA 只首帧 %d 镜 → %d 张图" % (len(i2), len(i2)))
    print("  FL2VA 首尾帧 %d 镜 → %d 张图" % (len(fl), 2 * len(fl)))
    print("  关键帧合计 %d 张" % imgs)
    miss_last = [s["seg"] for s in fl if not s.get("keyframe_last")]
    miss_first = [s["seg"] for s in shots if not s.get("keyframe_first")]
    print("  缺尾帧描述：" + ("无" if not miss_last else ", ".join(miss_last)))
    print("  缺首帧描述：" + ("无" if not miss_first else ", ".join(miss_first)))
    over_cast = [s["seg"] for s in shots if len(s["chars"]) > 2]
    print("  超 2 个角色：" + ("无" if not over_cast else ", ".join(over_cast)))

    print("\n【节奏】")
    print("  空镜（无人物）%d 镜 / %d 秒 = 全片 %.1f%%"
          % (len(no_cast), sec_no_cast, 100.0 * sec_no_cast / total if total else 0))
    print("  无台词镜 %d 镜 / %d 秒 = 全片 %.1f%%"
          % (len(no_lines), sec_no_lines, 100.0 * sec_no_lines / total if total else 0))
    print("  台词密度 %.2f 中文字/秒（4–8 岁旁白舒适区约 2.5–3.5）"
          % (cjk / total if total else 0))
    if no_cast:
        print("  空镜清单：")
        for s in no_cast:
            print("    · %-30s %2d 秒  %s" % (s["seg"], s["dur"], s["visual"][:30]))


# ----------------------------------------------------------------- 输出
def _open_out(path, encoding, newline=None):
    """目标文件被 Excel 等程序占用时不硬覆盖，降级另存并提示。"""
    try:
        return open(path, "w", encoding=encoding, newline=newline), path
    except PermissionError:
        base, ext = os.path.splitext(path)
        alt = base + "_new" + ext
        print("  ! %s 被占用（Excel？），本次写入 %s"
              % (os.path.basename(path), os.path.basename(alt)))
        return open(alt, "w", encoding=encoding, newline=newline), alt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ep", help="集号（01）或配置路径")
    ap.add_argument("--audit", action="store_true", help="只体检，不写文件")
    ap.add_argument("--locks", default=LOCKS_PATH)
    ap.add_argument("--out", default=None, help="覆盖输出目录")
    ap.add_argument("--with-table", action="store_true", help="同时输出 13 列全中文分镜大表")
    args = ap.parse_args()

    path = args.ep
    if not path.lower().endswith(".json"):
        path = os.path.join(EP_DIR, "ep%s.json" % str(args.ep).zfill(2))
    L = json.load(open(args.locks, encoding="utf-8"))
    ep = json.load(open(path, encoding="utf-8"))
    L = merge_local(L, ep.get("local"))

    nn = str(ep["ep"]).zfill(2)
    shots = ep["shots"]
    tc, total = timecodes(shots)

    if args.audit:
        audit(shots, ep, total)
        return

    out_dir = os.path.join(ROOT, args.out or ep["out_dir"])
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)

    # ---- video_config.json
    segs = []
    frames = []
    for i, s in enumerate(shots, 1):
        mode = s.get("mode", "i2va")
        a, b = frames_of(ep, i)
        seg = {
            "name": s["seg"],
            "mode": mode,
            "seconds": s["dur"],
            "first_frame": a,
            "last_frame": b if mode == "fl2va" else None,
            "prompt": build_prompt(s, L, ep, i, mode),
        }
        segs.append(seg)
        frames.append({
            "shot": i,
            "seg": s["seg"],
            "mode": mode,
            "seconds": s["dur"],
            "first_file": a,
            "last_file": b if mode == "fl2va" else None,
            "first_prompt_cn": s.get("cn_first", ""),
            "last_prompt_cn": s.get("cn_last", ""),
            "first_prompt_en": s.get("keyframe_first", ""),
            "last_prompt_en": s.get("keyframe_last", ""),
        })

    cfg = {
        "project_name": ep["project_name"],
        "comfyui_url": ep.get("comfyui_url", "http://127.0.0.1:8188"),
        "paths": {
            "comfyui_dir": ep["comfyui_dir"],
            "output_base_dir": ep["output_base_dir"],
        },
        "video": ep["video"],
        "reference_images": ep["reference_images"],
        "segments": segs,
    }
    json_path = os.path.join(out_dir, "video_config.json")
    f, json_path = _open_out(json_path, "utf-8")
    with f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    fr_path = os.path.join(out_dir, "05_关键帧清单_EP%s.json" % nn)
    f, fr_path = _open_out(fr_path, "utf-8")
    with f:
        json.dump({"ep": nn, "frames": frames}, f, ensure_ascii=False, indent=2)

    csv_path = ""
    if args.with_table:
        csv_path = os.path.join(out_dir, "03_分镜表_EP%s.csv" % nn)
        f, csv_path = _open_out(csv_path, "utf-8-sig", newline="")
        with f:
            w = csv.writer(f, quoting=csv.QUOTE_ALL)
            w.writerow(CSV_HEADER)
            for i, s in enumerate(shots, 1):
                mode = s.get("mode", "i2va")
                w.writerow([
                    i, MODE_CN.get(mode, mode), s["dur"], s["scene"], s["visual"], s["line"],
                    s["cn_cam"], L["lights"][s["light"]]["cn"],
                    s.get("cn_first", ""),
                    s.get("cn_last", "") if mode == "fl2va" else "无（只出首帧）",
                    build_cn_video(s, L), s["sfx"], L["music"][s["music"]],
                ])

    # ---- 统计
    en, cjk, r = ratio(shots)
    print("第 %s 集：%d 镜，合计 %d 秒" % (nn, len(shots), total))
    print("英文占比实测 %.1f%%（英词 %d / 中字 %d）" % (r * 100, en, cjk))
    pr, usable = plan_ratio(ep.get("cum_words"))
    if pr is not None:
        print("按大纲 V3.0 §1.6 外推 %.1f%%（累计新词 %d → 可表达 %d）；该节只考核 18/34/59/83/90 集"
              % (pr * 100, ep["cum_words"], usable))
    print("已写出：")
    print("  " + json_path)
    print("  " + fr_path)
    if csv_path:
        print("  " + csv_path)
    audit(shots, ep, total)


if __name__ == "__main__":
    main()
