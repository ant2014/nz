# -*- coding: utf-8 -*-
"""
EP01 分镜单一数据源。
一次运行，生成三份互不漂移的产物：
  03_分镜表_EP01.csv       —— 审稿 / Excel 落地
  04_分镜提示词_EP01.md    —— 逐镜提示词（可直接投喂 H3）
  video_config.json        —— freevideo 链式生成配置
同时打印英文占比实测值（口径见 kids-bilingual-storyboard 的 english-ratio-policy）。
改分镜只改下面的 SHOTS，不要手改生成的三个文件。
"""
import csv
import json
import re
import os

HERE = os.path.dirname(os.path.abspath(__file__))
EP = "01"

# ---------------------------------------------------------------- 全局锁定串
STYLE = (
    "2D cel-shaded Chinese mythic fantasy animation, fine dark ink outlines of even weight, "
    "flat colour fills with one hard-edged shadow layer, hand-painted watercolour skies, very "
    "subtle rice-paper grain, no 3D rendering, no photoreal skin, no lens flare, no chromatic "
    "bloom; character designs, colours, proportions and line weight must match the supplied "
    "reference sheets exactly."
)

NEG = (
    "NEGATIVE: no on-screen text or lettering of any kind, no modern objects, no plastic, no "
    "photorealistic skin or 3D render, no lens flare or bloom, no Japanese anime eye sparkles, "
    "no extra characters beyond those described, no adult-proportioned child, no full-body "
    "dragon, no change to the fixed landmarks of this scene."
)

SC = {
    "S02-1": (
        "a Chinese courtyard mansion's open inner court, grey brick paving in a herringbone "
        "pattern running diagonally north-east, six vermilion columns around a covered walkway, "
        "a three-step stone stair to the main house at the top third with a worn hollow on the "
        "second step, a stone well with rope marks on the rim on the west side, an old plum tree "
        "leaning south-east with one empty birdcage hanging in its branches, a bamboo laundry pole "
        "on two stands on the east side, a low grey brick wall at the south edge, whitewashed walls, "
        "warm late-afternoon sunlight."
    ),
    "S02-2": (
        "a covered wooden corridor in a Chinese courtyard mansion in one-point perspective, "
        "vermilion columns on both sides at 2.4m spacing with round stone plinths, three red "
        "lanterns hanging overhead, paper-lattice windows at the far end, grey brick floor, "
        "afternoon light cutting across the corridor in warm bars."
    ),
    "S03-1": (
        "a formal Chinese hall interior, dark wooden beams overhead, a long altar table 2.4m wide "
        "across the middle of frame, a five-piece celadon tea set on it with two chipped cup rims, "
        "two high-backed chairs set symmetrically, a six-panel folding screen behind painted with "
        "sea waves and clouds with a crack running through the middle panel, a dark plaque with an "
        "ink block on the beam, lattice windows with paper panes, soft indoor daylight."
    ),
    "SKY-1": (
        "high above a coastal town, three layered cloud banks, a flat cloud platform at the lower "
        "centre whose edge curls into a cloud tongue, the town's grey roofs reduced to thumbnail "
        "size far below, one tiny red lantern glowing at 40% of frame width on the lower left, "
        "cold blue high-altitude light with warm cloud rims."
    ),
    # 本集局部插入镜：S02-1 正房门的地面以下局部（暗场），不是新场景
    "INS-1": (
        "the closed double-leaf wooden door of a courtyard mansion's main house seen from outside "
        "at night, dark aged wood with two old bolt marks on it, a heavy wooden threshold 0.35m "
        "high under the door, grey brick paving below the threshold, the door posts and the wall "
        "around them swallowed by near-darkness."
    ),
}

SC_CN = {
    "S02-1": (
        "S02-1 李府·庭院天井——青砖缝永远斜向东北；三级石阶在画面上方三分之一，第二级踏步有一道踩出的"
        "凹痕；石井＋老梅树（枝上挂一只空鸟笼）在左；晾衣杆在东；南缘矮墙 2.0m；白墙。本集为夜景状态，"
        "门内红光时要整院被染红。"
    ),
    "S02-2": (
        "S02-2 李府·回廊——一点透视，消失点在画面 48% 高度略偏右；左右朱柱柱距 2.4m、柱底圆鼓石础；"
        "头顶只许三盏红灯笼；廊尽头一扇纸窗；廊下阴影压住画面下半部。本集为夜景状态。"
    ),
    "S03-1": (
        "S03-1 李府·内堂——长条案 2.4m 横贯画面中段（案上固定五件青瓷、其中两只杯口有缺口）；案后六扇"
        "屏风，正中一扇有一道裂痕；两把高背椅对称；梁上悬一块只有墨块与金边的匾（不许出字）。本集为"
        "夜景＋红光状态。"
    ),
    "SKY-1": (
        "SKY-1 云端高空——三层云海（下暗、中白、上透）；下中一块平云台（边缘一道翻卷云舌，宽 3m，可站一人）；"
        "下方城屋顶缩成指甲盖大小（不许画清楚）；一点红灯笼在画面左下 40%。"
    ),
    "INS-1": (
        "INS-1 门缝插入镜——S02-1 正房门的局部，不属于新场景：暗旧木门（门上两道旧门栓印痕）、门下木门槛"
        "0.35m、门槛下青砖。画面几乎全黑，只留门缝一道红光。"
    ),
}

CH = {
    # 以定妆照为准的成片口径（与 bible_100 原文的差异见 01_参考文档 的对照表）
    "C01": (
        "a chubby Chinese toddler of about three, 95cm tall, barefoot, a cream-white short-sleeved "
        "under-shirt with a plain cloth tie at the back, a vermilion diamond-shaped bellyband with one "
        "thin pale-gold geometric border on it, indigo loose knee-length shorts, a wide matte-gold "
        "bangle on the right wrist, a thin gold anklet on the right ankle, a long vermilion silk sash "
        "wound once at the waist with both ends hanging down, black hair in two small top-knots tied "
        "with thin red cords, round amber eyes with two fixed highlight dots at their lower edge, "
        "a small three-petal vermilion flame mark at the centre of the forehead"
    ),
    "C02": (
        "a stern Chinese man of about forty, 180cm, low heavy brows, a neat short beard, hair in a "
        "topknot with a black crown, a dark indigo robe with an iron-grey mountain-pattern half armour "
        "over the chest and shoulders, a leather belt with a dull bronze buckle, a plain black-sheathed "
        "straight sword at his hip"
    ),
    "C03": (
        "a gentle Chinese woman of about thirty-five, 165cm, a soft round face, hair in a low bun with "
        "a plain silver hairpin, a dusty-pink crossed-collar robe with a cream inner collar, a deep "
        "brown leather belt and matching wrist wraps, deep grey-green trousers"
    ),
    "C04": (
        "an ancient Taoist master, 170cm, slightly stooped, wide-sleeved white robe with pale silver "
        "cloud embroidery, long white beard, a jade hairpin, a gourd at the waist, cloth sandals, "
        "a white horsehair whisk in his right hand"
    ),
    "MAID": (
        "a background household maid in pale lotus-white and grey-green cotton clothes with a cloth "
        "headband, her face kept out of focus and her eyes drawn as two plain dots"
    ),
    "STEWARD": (
        "a background elderly steward of about sixty in a deep-brown and grey cotton robe with a cloth "
        "headband and a ring of keys at his waist, his face kept out of focus and his eyes drawn as two "
        "plain dots"
    ),
}

CH_CN = {
    "C01": "哪吒（幼年 C01，95cm）：米白短袖内衫＋朱砂红菱形肚兜＋靛青及膝短裤，右腕宽金镯、右脚踝细金环，"
           "腰缠朱红长绫，发式两枚小揪揪以红绳扎，琥珀圆眼、眼内两点固定高光，额间三瓣朱红火焰纹，赤脚。",
    "C02": "李靖（C02，180cm）：深靛长袍＋铁灰山纹半甲＋皮腰带（暗铜扣）＋黑鞘直剑＋短须＋黑冠顶髻。",
    "C03": "殷夫人（C03，165cm）：藕荷色交领长衣＋米白内领＋深褐皮腰带与护腕＋深灰绿裤＋银簪低髻，温和面容。",
    "C04": "太乙真人（C04，170cm、微驼）：月白宽袖道袍＋银云纹＋长白须＋玉簪＋腰挂葫芦＋布鞋＋右手白拂尘。",
    "MAID": "侍女（群像口径，虚焦）：藕白＋灰绿棉布衣＋布头巾，不对脸（眼睛只画两点）。",
    "STEWARD": "老管家（群像口径，虚焦）：深褐＋灰棉袍＋布头巾＋腰间一串钥匙，不对脸（眼睛只画两点）。",
}

LT = {
    "S02-2_night": (
        "at night the three red lanterns are the only light source, casting three warm pools on the "
        "round stone plinths, the lower half of frame in cool blue moonlight, the far paper-lattice "
        "window unlit"
    ),
    "S02-2_night_moon": (
        "at night three red lanterns cast warm pools on the round stone plinths, the lower half of "
        "frame in cool blue moonlight, a pale moon visible beyond the corridor eaves"
    ),
    "S02-1_night": (
        "at night the three red lanterns throw warm bars across the grey brick paving, the whitewashed "
        "walls in cool blue moonlight, the plum tree casting long soft shadows, the worn hollow on "
        "the second step catching a thin rim of light"
    ),
    "S02-1_red": (
        "the courtyard is flooded with warm red light spilling out from under the closed door of the "
        "main house, the three red lanterns flattened into three thin shadows on the whitewashed wall, "
        "the grey brick paving washed red from the top third downward"
    ),
    "S02-1_red_settled": (
        "the courtyard holds a steady warm red wash from under the closed door of the main house, the "
        "three lanterns reduced to thin shadows, the whitewashed wall picking up a soft warm rim"
    ),
    "S03-1_red": (
        "the hall is flooded with warm red light from a glowing round shape on the floor, red rims "
        "along the altar table edge and the celadon rims, the beam shadows overhead almost black, "
        "everything past the table sunk in shadow"
    ),
    "S03-1_burst": (
        "a bright burst of red light from the floor floods the whole hall, one hard red rim on every "
        "edge of the altar table and the folding screen, the beam shadows swinging once, everything "
        "else pushed into near-black"
    ),
    "INS_red": (
        "the courtyard is in near-total darkness; one thin hard line of red light in the gap between "
        "the door leaves is the only light source"
    ),
    "INS_red_peak": (
        "near-total darkness with one thin hard line of red light at its brightest, the wooden threshold "
        "under the door catching a pale edge"
    ),
    "S03-1_lamp": (
        "at night the hall is lit only by one oil lamp on the altar table, a warm pool around the celadon "
        "tea set, the beams and the folding screen sinking into cool shadow, no red light"
    ),
    "SKY": "cold blue high-altitude light with warm cloud rims, the town far below in shadow",
}

LT_CN = {
    "S02-2_night": "夜：三盏红灯笼是唯一光源，柱础上落三团暖光；画面下半部冷蓝月光；廊尽头纸窗不亮。",
    "S02-2_night_moon": "夜：三盏红灯笼暖光落在柱础上；檐外可见一轮淡月；下半部冷蓝月光。",
    "S02-1_night": "夜：三盏红灯笼把暖光一道道打在青砖上；白墙偏冷蓝月光；梅树影子长而软；第二级凹痕有一线薄光。",
    "S02-1_red": "门内涌出的暖红光把整个院子染红，从画面上三分之一开始往下；三盏灯笼被压成墙上三道薄影。",
    "S02-1_red_settled": "院中红光收成一层稳定的暖色；灯笼只剩薄影；白墙挂上一层柔和暖边。",
    "S03-1_red": "堂屋被地上那团红光染满；条案边缘与青瓷杯口都带红边；梁架阴影几乎全黑；条案以外沉进暗部。",
    "S03-1_burst": "裂开的瞬间一团强红光炸满全堂；条案与屏风每一道边都有一条硬红边；梁影晃一下；其余压进近黑。",
    "INS_red": "几乎全黑；门缝里一道细而硬的红线是唯一光源。",
    "INS_red_peak": "近黑，门缝那道红光到最亮；门下木门槛被照出一道发白的边。",
    "S03-1_lamp": "夜：堂内只有条案上一盏油灯，暖光收在条案周围；梁架与屏风沉在冷调暗部；无红光。",
    "SKY": "高空冷蓝光，云边暖；下面那座城在阴影里。",
}

MUS = {
    "M_low": "A low sustained string note at a slow tempo, no melody, held through the shot and fading at the very end.",
    "M_quiet": ("Sparse low strings at a slow tempo with one sustained flute note over them, the volume "
                "dropping toward the end of the shot."),
    "M_drone": ("A single low drone at a slow tempo with a soft tremolo on the low strings, rising slightly "
                "and then holding."),
    "M_heart": ("One low drumbeat at a slow tempo under sustained strings, the drum stopping before the end "
                "of the shot."),
    "M_tender": ("Warm mid-register strings at a slow tempo, a quiet two-note phrase repeated, no percussion."),
    "M_cut": ("One low struck string note at a slow tempo, cutting off immediately after the crack and leaving "
              "silence."),
    "M_hook": ("A short rising phrase on low strings at a slow tempo, one struck bell tone at the top of the "
               "phrase, then both fade out."),
}

VO = ("The narrator (S1), a warm slow-paced storyteller with a clear gentle voice, says in an off-screen "
      "voiceover: ")


def vo(line):
    return VO + "<d>[Chinese] " + line + "</d> while every on-screen character's lips remain completely closed."


def lip(who, line, voice):
    return "%s, %s, says: <d>[Chinese] %s</d> his or her lips moving in sync with the words." % (who, voice, line)


# ---------------------------------------------------------------- 22 个镜头
# seg / 段 / 场景 / 时长 / 画面 / 台词 / 人物 / 动作 / 镜头 / 光 / 台词(英) / 声 / 乐 / 中文镜头 / 语言点
SHOTS = [
    dict(
        seg="ep01_s01_dark_door_red_light", part="前置钩子", scene="INS-1", dur=10,
        visual="暗场。门缝里一线红光一明一暗，亮两次、暗两次；画面里别的一动不动。",
        line="旁白：很久很久以前，陈塘关的将军府里，出了一件怪事——夫人怀了孩子，整整三年六个月，baby 还没出生。",
        chars=[], light="INS_red",
        action=("The courtyard side of the closed main-house door fills the frame, almost completely dark; a "
                "thin hard line of red light pulses in the narrow gap between the two door leaves, brightening, "
                "dimming and brightening again; nothing else in the frame moves."),
        camera=("The camera holds a static shot at 85mm with shallow depth of field, centred on the gap between "
                "the two door leaves."),
        dlg=vo("很久很久以前，陈塘关的将军府里，出了一件怪事——夫人怀了孩子，整整三年六个月，baby 还没出生。"),
        sfx=("A low continuous hum under near-silence; the wooden door frame ticks once as it settles; no other "
             "sound."),
        mus="M_low",
        cn_cam="固定机位（85mm、浅景深），画面只咬住两扇门之间那道缝。",
        words="首现：baby",
    ),
    dict(
        seg="ep01_s02_lanterns_sway", part="前置钩子", scene="S02-2", dur=8,
        visual="三盏红灯笼在夜风里晃；砖地与石础上的光斑跟着挪一点，又回来。",
        line="（无台词·环境声：夜风、灯笼绳吱呀）",
        chars=[], light="S02-2_night",
        action=("The three red lanterns hang overhead and swing gently in the night wind, each tilting a few "
                "degrees and settling; the warm light patches on the grey brick floor and the round stone "
                "plinths slide a few centimetres with each swing and return."),
        camera=("The camera holds a wide static shot at 24mm on the corridor's one-point perspective, the "
                "vanishing point at 48% of frame height and slightly right of centre."),
        dlg="none — no speech in this shot.",
        sfx=("Night wind moving along the corridor; lantern ropes creaking at short regular intervals; a faint "
             "hollow echo off the brick floor."),
        mus="M_quiet",
        cn_cam="全景固定（24mm），一点透视，消失点在 48% 高度、略偏右。",
        words="—",
    ),
    dict(
        seg="ep01_s03_lijing_paces", part="正片・上半段", scene="S02-2", dur=10,
        visual="李靖背影在廊下来回踱步，右手按剑柄，肩背绷直；他越过第一根、第二根朱柱，一直朝廊尽头那扇纸窗走，不回头。",
        line="旁白：廊下踱步的这个人，是 dad。This is dad.",
        chars=["C02"], light="S02-2_night",
        action=("Li Jing walks away from the camera along the corridor with his right hand resting on the sword "
                "hilt, his shoulders squared and his pace even; he passes the near vermilion column, then the "
                "second column, and keeps walking toward the far paper window without turning his head."),
        camera=("The camera follows him from behind in a tracking shot at slow speed, medium shot at 50mm, "
                "keeping him in the left third of the frame."),
        dlg=vo("廊下踱步的这个人，是 dad。This is dad."),
        sfx=("Slow measured footsteps on brick, cloth moving with each step, night wind in the corridor."),
        mus="M_quiet",
        cn_cam="背后跟拍（Tracking，慢速），中景 50mm，人物保持左三分。",
        words="首现：dad；核心句型 This is…（第1次）",
    ),
    dict(
        seg="ep01_s04_worn_dust_line", part="正片・上半段", scene="S02-2", dur=8,
        visual="地面特写：一双布鞋又落在同一条砖缝上；砖缝已被踩出一道浅浅的白灰线。脚跟落定，一缕细灰从缝里弹起，往左飘。",
        line="（无台词·脚步、衣料摩擦）",
        chars=["C02"], light="S02-2_night",
        action=("Li Jing's foot comes down on the same grey brick again; between the bricks a thin line of "
                "dust has already been worn pale by his repeated walking; the heel settles and a small dry puff "
                "of dust lifts from the seam and drifts left."),
        camera=("The camera holds a close detail shot at 85mm at floor level, shallow depth of field, static, "
                "the frame carrying only his feet, the hem of his dark indigo robe and the worn brick seam."),
        dlg="none — no speech in this shot.",
        sfx=("Footsteps on brick with a soft scuff of cloth at the end of each step; one small dry puff of dust."),
        mus="M_quiet",
        cn_cam="贴地细节特写（85mm、浅景深、固定），画面只留脚、袍角与那道砖缝。",
        words="—",
    ),
    dict(
        seg="ep01_s05_closed_door_cry", part="正片・上半段", scene="S02-1", dur=8,
        visual="院子这头抬眼看向正房：两扇门关得死死的；门缝里传出一声压着的痛呼，起了、撑住、又细下去。镜头小幅慢推。",
        line="旁白：房里的人，是 mom。This is mom.",
        chars=[], light="S02-1_night",
        action=("The main house door stays shut at the top of the three-step stone stair; the two door leaves "
                "do not move; behind them a woman's muffled cry rises through the wood, holds, and thins out."),
        camera=("The camera pushes in with small amplitude at slow speed toward the closed door at 50mm, the "
                "three-step stair in the lower third of the frame."),
        dlg=vo("房里的人，是 mom。This is mom."),
        sfx=("A muffled woman's cry through thick wood; hurried cloth and small footsteps inside the house; "
             "night wind under the eaves."),
        mus="M_low",
        cn_cam="小幅慢速推近（Push In，50mm），三级石阶压在下三分之一。",
        words="首现：mom；核心句型 This is…（第2次）",
    ),
    dict(
        seg="ep01_s06_steward_tea", part="正片・上半段", scene="S02-2", dur=8,
        visual="老管家从画面右缘端茶进来，在李靖身后一步停住、低头说话；李靖没回头，老人便蹲下，把茶碗搁在近处朱柱底的圆石础上，再直起腰。",
        line="老管家：将军，您歇会儿吧。夫人吉人天相。",
        chars=["C02", "STEWARD"], light="S02-2_night",
        action=("The old steward walks in from the right edge of frame carrying one tea bowl on a wooden tray; "
                "he stops one step behind Li Jing and lowers his head to speak; Li Jing does not turn, so the "
                "steward crouches and sets the bowl down on the round stone plinth at the base of the near vermilion "
                "column, then straightens."),
        camera=("The camera holds a medium shot at 50mm, static, Li Jing in the left third seen from behind, "
                "the steward entering from the right edge and stopping in the right third."),
        dlg=lip("The old steward (S2)", "将军，您歇会儿吧。夫人吉人天相。",
                "an elderly male voice, low and careful"),
        sfx=("Soft footsteps, a wooden tray tapping, and the thin ring of porcelain set down on stone."),
        mus="M_quiet",
        cn_cam="中景固定（50mm），李靖背影在左三分，老管家从右缘入画停在右三分。",
        words="—",
    ),
    dict(
        seg="ep01_s07_lijing_sighs", part="正片・上半段", scene="S02-2", dur=8,
        visual="李靖停步，抬头看廊檐外的月亮，长长吐一口气，胸口落下去；右手一直没离开剑柄。镜头小幅慢速上摇。",
        line="李靖：三年六个月了。寻常孩子十个月就落地，这一胎太久了。",
        chars=["C02"], light="S02-2_night_moon",
        action=("Li Jing stops walking, lifts his head toward the moon beyond the corridor eaves, and lets out "
                "one long breath, his chest dropping; his right hand stays on the sword hilt."),
        camera=("The camera tilts up with small amplitude at slow speed from his shoulder toward the eaves "
                "and the moon, 50mm."),
        dlg=lip("Li Jing (S3)", "三年六个月了。寻常孩子十个月就落地，这一胎太久了。",
                "a low restrained adult male voice, speaking slowly"),
        sfx="Night wind, lantern ropes creaking, one long exhale.",
        mus="M_quiet",
        cn_cam="小幅慢速上摇（Tilt Up，50mm），从肩头摇到檐角与月亮。",
        words="—",
    ),
    dict(
        seg="ep01_s08_red_flood", part="正片・上半段", scene="S02-1", dur=10,
        visual="正房门底下红光涌出来，一波扫下三级石阶，把整院青砖染红；梅树影子晃了一下；墙上三盏灯笼被压成薄薄三道影。",
        line="（无台词·只留低频嗡）",
        chars=[], light="S02-1_red",
        action=("Red light bursts out from under the closed door of the main house and sweeps down the three-step "
                "stone stair across the whole courtyard in one wave; the grey brick paving turns red from the "
                "top third downward, the plum tree's shadow swings once, and the three lanterns flatten into three "
                "thin shadows on the whitewashed wall."),
        camera=("The camera holds a wide establishing shot at 24mm from the courtyard, the main house at the "
                "top third, static, full depth of field."),
        dlg="none — no speech in this shot.",
        sfx=("The night wind stops; one low continuous hum rises and holds; a single wooden tick from the door "
             "frame."),
        mus="M_drone",
        cn_cam="全景固定（24mm、全实），正房压在画面上三分之一。",
        words="—",
    ),
    dict(
        seg="ep01_s09_lotus_breeze", part="正片・上半段", scene="S02-1", dur=8,
        visual="风过院子；梅树叶子翻了一下、露出灰白叶背，又翻回去；枝上那只空鸟笼一动不动；墙上红光收成一层稳稳的暖色，不再跳。",
        line="旁白：一股莲花的香气，漫满了整个庭院。",
        chars=[], light="S02-1_red_settled",
        action=("A breeze moves through the courtyard; the plum tree's leaves turn over once showing their "
                "pale undersides and turn back; the empty birdcage hanging in the branches stays perfectly "
                "still; the red light on the whitewashed wall settles into a steady warm wash and stops pulsing."),
        camera=("The camera holds a close detail shot at 85mm, static, shallow depth of field, framing the "
                "plum tree's leaves and the empty birdcage."),
        dlg=vo("一股莲花的香气，漫满了整个庭院。"),
        sfx=("Leaves turning over in a light breeze, a faint dry creak from the birdcage rope, the low hum "
             "quieting."),
        mus="M_low",
        cn_cam="细节特写（85mm、浅景深、固定），框住梅叶与空鸟笼。",
        words="—",
    ),
    dict(
        seg="ep01_s10_grip_hilt", part="正片・上半段", scene="S02-2", dur=6,
        visual="特写：李靖攥紧剑柄，指节发白，不眨眼；身后石础上一道红光闪了一下。镜头小幅慢推。",
        line="（无台词·心跳声放大）",
        chars=["C02"], light="S02-2_night",
        action=("Li Jing's fingers close tighter around the sword hilt until his knuckles pale; he does not "
                "blink; behind him the red light flickers once across the round stone plinth."),
        camera=("The camera pushes in with small amplitude at slow speed toward his right hand on the sword "
                "hilt at 85mm, shallow depth of field, the closed door small and soft in the background."),
        dlg="none — no speech in this shot.",
        sfx="One amplified heartbeat under a held low hum; leather creaking as the grip tightens.",
        mus="M_heart",
        cn_cam="小幅慢速推近（85mm、浅景深），落在握着剑柄的手上；关门在远处虚焦。",
        words="—",
    ),
    dict(
        seg="ep01_s11_red_peak_freeze", part="中段小钩子", scene="INS-1", dur=5,
        visual="定格：门缝那道红光到最亮，撑住不动；门下木门槛被照得发白。画面里没有一样东西在动。",
        line="旁白：有东西，裂开了！",
        chars=[], light="INS_red_peak",
        action=("The red light in the door gap reaches its brightest and holds; the wooden threshold below the "
                "door glows pale; nothing in the frame moves."),
        camera="The camera holds a static shot at 85mm at threshold height, shallow depth of field.",
        dlg=vo("有东西，裂开了！"),
        sfx="The hum peaks and holds; one sharp crack from behind the door, then silence.",
        mus="M_cut",
        cn_cam="固定机位（85mm、门槛高度、浅景深），定格不许动。",
        words="—",
    ),
    dict(
        seg="ep01_s12_maid_bursts", part="正片・下半段", scene="S03-1", dur=8,
        visual="侍女从里面一把拉开右扇门，红光顺着地砖扑进来、漫过她的脚；她往前踉跄一步，手在抖，脸一直半偏着往屋里看。",
        line="侍女：将军！夫人生了……生了个肉球！",
        chars=["MAID"], light="S03-1_red",
        action=("A maid drags the right door leaf open from inside and stumbles one step into the opening; "
                "red light floods across the grey brick floor past her feet; her hands shake and she keeps her "
                "head half turned back toward the room."),
        camera=("The camera holds a medium shot at 50mm, static, the door on the left third, the maid "
                "entering the frame from the left."),
        dlg=lip("The maid (S4)", "将军！夫人生了……生了个肉球！",
                "a young female voice, high and breathless"),
        sfx=("The door leaf dragging on stone, one sharp wooden knock as it opens, quick shallow breathing."),
        mus="M_drone",
        cn_cam="中景固定（50mm），门在左三分，侍女从左侧入画。",
        words="—",
    ),
    dict(
        seg="ep01_s13_flesh_ball_spins", part="正片・下半段", scene="S03-1", dur=10,
        visual="低机位特写：一只圆滚滚的粉肉球在条案前的青砖地上滴溜溜打转，周身裹着红光，红光扫过案腿；它慢慢减下来，晃了两晃，还在转。",
        line="（无台词·香气、轻响）",
        chars=[], light="S03-1_red",
        action=("A round pink flesh ball the size of a small melon spins on the grey brick floor in front of "
                "the altar table, ringed by red light that spills across the table legs; it slows, wobbles, "
                "and keeps turning in place."),
        camera=("The camera holds a low close shot at 85mm, static, the ball centred on the brick floor, "
                "shallow depth of field, the altar table legs soft behind it."),
        dlg="none — no speech in this shot.",
        sfx=("A soft wet spinning sound on brick, a faint high hum from the light, shallow breathing from the "
             "daybed."),
        mus="M_drone",
        cn_cam="低机位特写（85mm、固定），肉球居中在砖地上，案腿虚焦在后。",
        words="—",
    ),
    dict(
        seg="ep01_s14_lady_yin_pale", part="正片・下半段", scene="S03-1", dur=6,
        visual="殷夫人靠在矮榻的靠枕上，脸白，两只手抓着被角，肩头一起一伏；眼睛盯在地上那只肉球上。",
        line="（无台词·急促呼吸）",
        chars=["C03"], light="S03-1_red",
        action=("Lady Yin leans back against the head of a low cushioned daybed set behind the altar table, "
                "her face pale, both hands gripping the edge of the quilt, her shoulders rising with each short "
                "breath; her eyes stay fixed on the ball on the floor."),
        camera=("The camera holds a medium shot at 50mm, static, her hands and the quilt in the lower third "
                "of frame."),
        dlg="none — no speech in this shot.",
        sfx="Short shallow breathing close to the microphone, cloth shifting under her hands.",
        mus="M_low",
        cn_cam="中景固定（50mm），手与被角压在下三分之一。",
        words="—",
    ),
    dict(
        seg="ep01_s15_sword_drawn", part="正片・下半段", scene="S03-1", dur=8,
        visual="李靖从画面左缘跨进来，一次抽出腰间宝剑，剑身在红光里拉出一道长亮；他把剑半举，剑尖斜指地上那只肉球。",
        line="李靖：妖物？",
        chars=["C02"], light="S03-1_red",
        action=("Li Jing steps in from the left edge of frame, draws the straight sword from his hip in one "
                "pull, the blade catching a long red highlight along its edge; he holds it half raised with "
                "the tip angled down toward the ball on the floor."),
        camera=("The camera holds a medium close-up at 85mm, static, the drawn sword crossing the frame "
                "diagonally."),
        dlg=lip("Li Jing (S3)", "妖物？", "the same low restrained adult male voice, cold"),
        sfx="Steel sliding out of the scabbard in one clean draw, then a held silence.",
        mus="M_heart",
        cn_cam="中近景固定（85mm），拔出的剑斜穿画面。",
        words="—",
    ),
    dict(
        seg="ep01_s16_blade_splits_ball", part="正片・下半段", scene="S03-1", dur=8,
        visual="剑一刀直劈下去，剑锋碰到球顶；球顺着刀口裂开，光从裂口里炸出来，整座堂屋被红光照满；两瓣球在砖上各自晃开。",
        line="（无台词·脆响、光爆）",
        chars=["C02"], light="S03-1_burst",
        action=("The blade comes down in one straight arc and strikes the top of the ball; the ball splits "
                "along the line of the cut and light bursts outward from the opening, washing the whole hall "
                "red, the two halves rocking apart on the brick."),
        camera=("The camera pushes in with small amplitude at fast speed as the blade lands, 50mm."),
        dlg="none — no speech in this shot.",
        sfx="One sharp crack, then a bright ringing burst of light, brick grit scattering.",
        mus="M_drone",
        cn_cam="落刀瞬间小幅快速推近（Push In，50mm）。",
        words="—",
    ),
    dict(
        seg="ep01_s17_boy_lands_laughs", part="正片・下半段", scene="S03-1", dur=10,
        visual="一个小娃娃从球里落下来，两只赤脚踩稳在砖上，膝一屈就站直了；他抬头咯咯地笑，圆眼睛里落着两点红光。画面左下角还留着李靖举剑的手臂。",
        line="旁白：他落地，站得稳稳的，还咯咯地笑——完全不像刚出生的 baby。",
        chars=["C01", "C02"], light="S03-1_red",
        action=("A chubby toddler drops out of the split ball and lands on both bare feet on the grey brick "
                "floor, knees bent, then straightens and stands firm; he looks up and laughs, his round amber eyes "
                "catching two red highlights; Li Jing's sword arm stays in the lower left corner of the frame, "
                "still raised."),
        camera=("The camera holds a medium shot at 50mm, static, the boy centred, his 95cm height readable "
                "against the 0.9m altar table behind him."),
        dlg=vo("他落地，站得稳稳的，还咯咯地笑——完全不像刚出生的 baby。"),
        sfx=("A soft landing of bare feet on brick, one clear child's laugh, the low hum dropping away."),
        mus="M_tender",
        cn_cam="中景固定（50mm），孩子居中；95cm 身高对着身后 0.9m 条案，比例必须读得出来。",
        words="复现：baby（本集第2次）",
    ),
    dict(
        seg="ep01_s18_bangle_sash_closeup", part="正片・下半段", scene="S03-1", dur=10,
        visual="特写：他右腕一转，金镯在红光里亮起一道硬金边；镜头顺着腰间的朱红长绫向左横移，绫尾抬了一下，两端那道暗金缠枝纹也亮了一下。",
        line="旁白：右手一只金镯，腰上一条红绫——这两样，是他生下来就带的。",
        chars=["C01"], light="S03-1_red",
        action=("The boy turns his right wrist; the wide gold bangle on it takes the red light and throws one "
                "hard gold highlight along its rim; the camera moves left along the long vermilion sash wound "
                "at his waist, whose tip lifts and swings once, the dark-gold vine border catching the same light."),
        camera=("The camera holds a close detail shot at 85mm, then pans left with small amplitude at slow "
                "speed from the bangle to the sash."),
        dlg=vo("右手一只金镯，腰上一条红绫——这两样，是他生下来就带的。"),
        sfx="Silk moving against silk, one soft metallic ring from the bangle.",
        mus="M_tender",
        cn_cam="细节特写（85mm）→ 小幅慢速左摇（Pan Left），从金镯摇到腰间红绫。",
        words="—",
    ),
    dict(
        seg="ep01_s19_cup_smashed", part="正片・下半段", scene="S03-1", dur=8,
        visual="他小手一横挥出去，条案上一只青瓷杯离了案沿、落地，在青砖上碎成几片，滑出半尺停住。",
        line="侍女（画外）：呀——！（当啷）",
        chars=["C01"], light="S03-1_red",
        action=("The boy swings one small hand sideways; a celadon cup on the altar table leaves the table "
                "edge, falls, and breaks on the grey brick floor into pieces that slide half a metre and stop."),
        camera="The camera holds a medium shot at 50mm, static, the altar table on the right third.",
        dlg=("The maid (S4), off-screen behind the camera, gives one short high startled cry: "
             "<d>[Chinese] 呀！</d> No on-screen character speaks, and the boy's lips stay closed."),
        sfx="Porcelain hitting brick, one sharp break, fragments sliding, the maid's cry.",
        mus="M_heart",
        cn_cam="中景固定（50mm），条案在右三分。",
        words="—",
    ),
    dict(
        seg="ep01_s20_mother_reaches", part="正片・下半段", scene="S03-1", dur=8,
        visual="殷夫人撑起一只胳膊，另一只手朝孩子伸出去；李靖把剑收回鞘里，从右缘跨上前来，停在条案边。",
        line="殷夫人：我的 baby……",
        chars=["C03", "C02"], light="S03-1_red",
        action=("Lady Yin pushes herself up on one elbow on the daybed and reaches her free hand out toward "
                "the boy; Li Jing sheathes the sword in one motion and steps in from the right, stopping at "
                "the near edge of the altar table."),
        camera=("The camera holds a medium shot at 50mm, static, the daybed on the left third, Li Jing "
                "entering from the right edge."),
        dlg=lip("Lady Yin (S5)", "我的 baby……", "a gentle female voice, weak and unsteady"),
        sfx="Quilt shifting, steel sliding back into the scabbard, one slow step on brick.",
        mus="M_tender",
        cn_cam="中景固定（50mm），矮榻在左三分（本集临时道具：矮榻＋被褥，摆条案后方），李靖从右缘入画。",
        words="复现：baby（本集第3次）",
    ),
    dict(
        seg="ep01_s21_finger_touch", part="片尾大钩子", scene="S03-1", dur=6,
        visual="李靖蹲下来，跟孩子一样高，用两指指背轻轻碰了一下他软乎乎的脸蛋；孩子的小手抬起来，攥住他一根手指，两个人都不动了。",
        line="（无台词·呼吸声、笑）",
        chars=["C01", "C02"], light="S03-1_red",
        action=("Li Jing crouches to the boy's height and touches the back of two fingers to the boy's soft "
                "cheek; the boy's small hand comes up and closes around one of his fingers, and neither of "
                "them moves."),
        camera=("The camera holds a close-up at 85mm, static, shallow depth of field on the two hands and "
                "the cheek."),
        dlg="none — no speech in this shot.",
        sfx="One held breath, a small child's breath, a quiet laugh; no speech.",
        mus="M_tender",
        cn_cam="特写固定（85mm、浅景深），落在两只手与脸蛋上。",
        words="—",
    ),
    dict(
        seg="ep01_s22_cloud_nod", part="片尾大钩子", scene="SKY-1", dur=12,
        visual="云头上一块平云台，白胡子老道站在下中，背侧三刻面；白眉眉尾往上翘着，胡须与拂尘都不动。他朝下面那座缩成指甲盖的城点了一下头；云台边缘那道云舌慢慢往外卷。",
        line="旁白：千里之外的乾元山，太乙真人正看着陈塘关点头。灵珠子，降生了。这位老神仙，很快就要登门。",
        chars=["C04"], light="SKY",
        action=("Taiyi Zhenren stands on the flat cloud platform at the lower centre, seen from behind at "
                "three quarters; his wide-sleeved white robe and his horsehair whisk stay still; the upturned "
                "tips of his white eyebrows show past the side of his head; he nods once toward the town far "
                "below; the cloud tongue at the platform's edge curls slowly outward."),
        camera=("The camera holds a wide static shot at 24mm, the platform at the lower centre, the layered "
                "cloud banks filling the upper two thirds, the town's roofs reduced to thumbnail size far below."),
        dlg=vo("千里之外的乾元山，太乙真人正看着陈塘关点头。灵珠子，降生了。这位老神仙，很快就要登门。"),
        sfx=("High-altitude wind moving across layered cloud, one wide sleeve lifting and settling once, a "
             "single distant bell tone."),
        mus="M_hook",
        cn_cam="全景固定（24mm），云台在下中，三层云海占上方三分之二，城屋顶只有指甲盖大小。",
        words="—",
    ),
]

# ------------------------------------------------------- 可选附录：跟读段（只在 MD 里给，不进 CSV/JSON）
APPEND = [
    dict(
        seg="ep01_x01_repeat_baby", part="附录·可选跟读", scene="S03-1", dur=8,
        visual="（可选）孩子坐在条案沿上，两条小腿垂着，正对镜头；他抬起一只手拍了两下自己的胸口，咯咯笑。",
        line="旁白：跟老师念——baby。Baby! Is this a baby? Yes, a baby!",
        chars=["C01"], light="S03-1_lamp",
        action=("The toddler sits on the edge of the altar table with both legs dangling, facing the camera; "
                "he lifts one small hand and taps his own chest twice, then laughs."),
        camera=("The camera holds a medium shot at 50mm, static, the boy centred against the six-panel "
                "folding screen."),
        dlg=vo("跟老师念——baby。Baby! Is this a baby? Yes, a baby!"),
        sfx="A wooden table edge creaking under small feet, one child's laugh, quiet night room tone.",
        mus="M_tender",
        cn_cam="中景固定（50mm），孩子居中，背景是六扇屏风。",
        words="复现：baby（跟读）",
    ),
    dict(
        seg="ep01_x02_repeat_dad", part="附录·可选跟读", scene="S03-1", dur=8,
        visual="（可选）孩子站在条案前正对镜头，抬起一只胳膊往身后指；李靖蹲在他左肩后侧，一只手平放在案沿上。",
        line="旁白：This is dad。Dad! Say it——dad。Dad!",
        chars=["C01", "C02"], light="S03-1_lamp",
        action=("The toddler stands in front of the altar table facing the camera and raises one arm to point "
                "backward at Li Jing, who crouches behind the boy's left shoulder with one hand flat on the "
                "table edge."),
        camera=("The camera holds a medium shot at 50mm, static, the boy in the centre and Li Jing low behind "
                "his left shoulder."),
        dlg=vo("This is dad。Dad! Say it——dad。Dad!"),
        sfx="A hand settling on wood, one child's breath, quiet night room tone.",
        mus="M_tender",
        cn_cam="中景固定（50mm），孩子居中，李靖低蹲在其左肩后。",
        words="复现：dad（跟读）＋核心句型 This is…",
    ),
]

# ---------------------------------------------------------------- 组装


def build_prompt(s):
    chars = "; ".join(CH[k] for k in s["chars"])
    chars_txt = ("CHARACTER LOCK: " + chars.rstrip(". ") + ". ") if chars else "CHARACTER LOCK: none, no figure in this shot. "
    desc = (
        "[Shot 1] " + STYLE + " SETTING LOCK (identical in every shot of scene " + s["scene"] + "): "
        + SC[s["scene"]] + " "
        + chars_txt
        + "ACTION: " + s["action"] + " "
        + "CAMERA: " + s["camera"] + " "
        + "LIGHTING: " + LT[s["light"]].rstrip(". ") + ". "
        + "DIALOGUE: " + s["dlg"] + " "
        + NEG
    )
    return (
        "integrated_multimodal_description: " + desc
        + "\n\noverall_soundscape: " + s["sfx"]
        + "\n\nnon_diegetic_music: " + MUS[s["mus"]]
    )


def build_cn(s):
    chars = "；".join(CH_CN[k] for k in s["chars"]) if s["chars"] else "本镜不出现人物，只出空景（按场景卡执行）。"
    return (
        "【场景·固定】" + SC_CN[s["scene"]] + "\n"
        "【人物】" + chars + "\n"
        "【画面】" + s["visual"] + "\n"
        "【镜头】" + s["cn_cam"] + "\n"
        "【光线】" + LT_CN[s["light"]] + "\n"
        "【配音与字幕·同一条轨道】" + s["line"] + "\n"
        "【禁止】画面不出现任何文字字幕或招牌字、不加现代物件、不做写实皮肤与三维渲染、不出现设定外的人物；"
        "本场景固定地标每个镜头都必须原样保留。"
    )


def timecodes():
    t = 0
    out = []
    for s in SHOTS:
        out.append("%d:%02d–%d:%02d" % (t // 60, t % 60, (t + s["dur"]) // 60, (t + s["dur"]) % 60))
        t += s["dur"]
    return out, t


def ratio(shots=None):
    """英文占比 = 英词数 /(英词数 + 中文字数/1.5)，口径同 english-ratio-policy。"""
    text = " ".join(s["line"] for s in (shots or SHOTS))
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    en = len(re.findall(r"[A-Za-z']+", text))
    return en, cjk, en / (en + cjk / 1.5)


def main():
    tc, total = timecodes()

    # ---- CSV
    csv_path = os.path.join(HERE, "03_分镜表_EP01.csv")
    header = ["集数", "剧情段落", "镜头号", "场景", "时间码", "时长(秒)",
              "画面内容（中文分镜意图）", "台词与字幕（单条轨道·中英混排）",
              "MiniMax H3 提示词（英文·可直接投递）", "中文提示词对照", "本镜语言点"]
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(header)
        for i, s in enumerate(SHOTS, 1):
            w.writerow([EP, s["part"], i, s["scene"], tc[i - 1], s["dur"], s["visual"], s["line"],
                        build_prompt(s), build_cn(s), s["words"]])

    # ---- MD 提示词
    md_path = os.path.join(HERE, "04_分镜提示词_EP01.md")
    lines = []
    lines.append("# 第 01 集 · 逐镜 H3 提示词（可直接投喂 / 正文 %d 镜 %d 秒 ＋ 附录可选跟读 %d 段）\n"
                 % (len(SHOTS), total, len(APPEND)))
    lines.append("> 每个代码块就是一段 video_config 的 `prompt`，一字不改粘过去即可。")
    lines.append("> 英文投喂，中文只作对照；画面一律无字幕，字幕后期贴。\n")
    acc = 0
    for i, s in enumerate(SHOTS, 1):
        lines.append("---\n")
        lines.append("## 镜 %02d ｜ %s ｜ %s ｜ %d 秒 ｜ %s\n" % (i, s["scene"], s["part"], s["dur"], tc[i - 1]))
        lines.append("- **画面**：" + s["visual"])
        lines.append("- **镜头**：" + s["cn_cam"])
        lines.append("- **光线**：" + LT_CN[s["light"]])
        lines.append("- **台词·字幕**：" + s["line"])
        lines.append("- **语言点**：" + s["words"])
        lines.append("- **分段名**：`" + s["seg"] + "`\n")
        lines.append("```text")
        lines.append(build_prompt(s))
        lines.append("```\n")
        acc += s["dur"]

    # ---- 附录：可选跟读段
    lines.append("\n---\n")
    lines.append("# 附录・可选跟读段（默认不拍）\n")
    lines.append("> 只为补英文占比而设。加进来总长变 199 秒，并会让\"片尾钩子落在最后\"这条结构规矩失效——")
    lines.append("> 要加请在 README 的待确认 #2 里拍板，然后手动追加到 `video_config.json` 的 segments 末尾与 CSV。\n")
    for i, s in enumerate(APPEND, 1):
        lines.append("## 附 %02d ｜ %s ｜ %s ｜ %d 秒\n" % (i, s["scene"], s["part"], s["dur"]))
        lines.append("- **画面**：" + s["visual"])
        lines.append("- **镜头**：" + s["cn_cam"])
        lines.append("- **台词·字幕**：" + s["line"])
        lines.append("- **分段名**：`" + s["seg"] + "`\n")
        lines.append("```text")
        lines.append(build_prompt(s))
        lines.append("```\n")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---- video_config.json
    cfg = {
        "project_name": "nezha_ep01",
        "comfyui_url": "http://127.0.0.1:8188",
        "paths": {
            "comfyui_dir": "D:/ComfyUI",
            "output_base_dir": "D:/msp/001-nz-db/成片",
        },
        "video": {"width": 1184, "height": 672, "default_seconds": 8,
                  "base_steps": 8, "refine_steps": 3},
        "reference_images": [
            "EP01_C01_nezha_child.png",
            "EP01_C02_lijing.png",
            "EP01_C03_lady_yin.png",
        ],
        "segments": [{"name": s["seg"], "seconds": s["dur"], "prompt": build_prompt(s)} for s in SHOTS],
    }
    json_path = os.path.join(HERE, "video_config.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    en, cjk, r = ratio()
    en2, cjk2, r2 = ratio(SHOTS + APPEND)
    print("片段 %d 段，合计 %d 秒（单段 5–12 秒，全部落在 H3 的 4–15 秒区间）" % (len(SHOTS), total))
    print("英文占比实测：正文 %.1f%%（英词 %d / 中字 %d）；加 2 段跟读后 %.1f%%（英词 %d / 中字 %d，总长 %d 秒）"
          % (r * 100, en, cjk, r2 * 100, en2, cjk2, total + sum(a["dur"] for a in APPEND)))
    print("目标（english-ratio-policy 第 1 集）20%%；偏差 %.1f 个百分点，原因写进 README 待确认 #2。" % (abs(r * 100 - 20)))
    print("已写出：")
    for p in (csv_path, md_path, json_path):
        print("  " + p)


if __name__ == "__main__":
    main()
