#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
以 Pillow 產生系統架構圖 PNG：docs/architecture.png

相依：
  pip install pillow

使用：
  python tools/render_arch.py
"""

from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture.png"

W, H = 1600, 900
BG = (255, 255, 255)
STROKE = (30, 30, 30)
TITLE = (0, 67, 137)
ACCENT = (0, 120, 215)


def load_font(size=18):
    try:
        # 優先使用系統中文字型（若存在）
        for name in [
            "/System/Library/Fonts/PingFang.ttc",  # macOS
            "C:/Windows/Fonts/msjh.ttc",  # Windows 微軟正黑
            "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",  # Linux Noto
        ]:
            p = Path(name)
            if p.exists():
                return ImageFont.truetype(str(p), size)
    except Exception:
        pass
    return ImageFont.load_default()


def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    # Pillow >=10: use textbbox instead of getsize
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def draw_box(draw, xy, text, fill=(245, 248, 255), outline=STROKE, radius=14, pad=10, font=None):
    x1, y1, x2, y2 = xy
    # 簡單圓角框（四個角畫圓 + 連線）
    r = radius
    draw.rounded_rectangle(xy, radius=r, outline=outline, width=2, fill=fill)
    if font is None:
        font = load_font(20)
    # 文字多行換行
    maxw = x2 - x1 - 2 * pad
    lines = []
    for part in text.split("\n"):
        buf = ""
        for ch in part:
            w, _ = _text_size(draw, buf + ch, font)
            if w > maxw and buf:
                lines.append(buf)
                buf = ch
            else:
                buf += ch
        lines.append(buf)
    # 置中繪製
    total_h = sum(_text_size(draw, t, font)[1] for t in lines) + (len(lines) - 1) * 6
    ty = y1 + (y2 - y1 - total_h) // 2
    for t in lines:
        tw, th = _text_size(draw, t, font)
        tx = x1 + (x2 - x1 - tw) // 2
        draw.text((tx, ty), t, fill=(15, 15, 15), font=font)
        ty += th + 6


def draw_arrow(draw, p1, p2, color=STROKE, width=3):
    # 畫線 + 小箭頭
    x1, y1 = p1
    x2, y2 = p2
    draw.line([p1, p2], fill=color, width=width)
    # 箭頭三角形
    import math
    angle = math.atan2(y2 - y1, x2 - x1)
    L = 12
    a1 = angle + math.radians(160)
    a2 = angle - math.radians(160)
    p3 = (x2 + L * math.cos(a1), y2 + L * math.sin(a1))
    p4 = (x2 + L * math.cos(a2), y2 + L * math.sin(a2))
    draw.polygon([p2, p3, p4], fill=color)


def main():
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title_font = load_font(36)
    body_font = load_font(20)

    # 標題
    title = "邊緣端語音指令系統 — 架構圖"
    tw, th = _text_size(draw, title, title_font)
    draw.text(((W - tw) // 2, 30), title, fill=TITLE, font=title_font)

    # 佈局座標
    mic = (80, 160, 260, 230)
    esp = (60, 260, 300, 430)
    broker = (480, 210, 720, 330)
    featS = (860, 260, 1160, 380)
    train = (1210, 220, 1520, 350)
    ota = (1210, 390, 1520, 480)
    mon = (480, 360, 720, 450)

    # 盒子
    draw_box(draw, mic, "INMP441\n麥克風", font=body_font)
    draw_box(draw, esp, "ESP32‑S3\nVAD / 特徵 (log‑Mel)\n學生模型 (KWS)\nMQTT Client", font=body_font)
    draw_box(draw, broker, "MQTT Broker GUI", font=body_font)
    draw_box(draw, mon, "監控 Client GUI\n訂閱 esp32/#", font=body_font)
    draw_box(draw, featS, "Feature Server\n訂閱 esp32/feat/#\n回覆 esp32/infer/{device}", font=body_font)
    draw_box(draw, train, "教師模型 + 週期性蒸餾(QAT)\n產生 int8 學生模型", font=body_font)
    draw_box(draw, ota, "模型發佈/OTA\n控制：esp32/control/{device}", font=body_font)

    # 連線/箭頭
    # mic -> esp
    draw_arrow(draw, (260, 195), (60, 340))
    # esp -> broker (feat 上行)
    draw_arrow(draw, (300, 320), (480, 270))
    draw.text((320, 270), "esp32/feat/{device}/{session}/{idx}", fill=ACCENT, font=load_font(16))
    # broker -> feat server
    draw_arrow(draw, (720, 270), (860, 320))
    # feat server -> broker -> esp (infer 回覆)
    draw_arrow(draw, (860, 300), (720, 240))
    draw_arrow(draw, (480, 240), (300, 300))
    draw.text((520, 210), "esp32/infer/{device}", fill=ACCENT, font=load_font(16))
    # status 到 monitor
    draw_arrow(draw, (300, 380), (480, 405))
    draw.text((330, 385), "esp32/status/{device}", fill=ACCENT, font=load_font(16))
    # 伺服器訓練循環
    draw_arrow(draw, (1160, 320), (1210, 290))
    draw_arrow(draw, (1365, 350), (1365, 390))
    # 控制到裝置
    draw_arrow(draw, (1210, 435), (720, 330))
    draw_arrow(draw, (480, 330), (300, 360))
    draw.text((760, 340), "esp32/control/{device}", fill=ACCENT, font=load_font(16))
    # 可選：原音塊到 monitor
    draw_arrow(draw, (300, 400), (480, 440))
    draw.text((320, 410), "esp32/audio/{ts}/{chunk}", fill=ACCENT, font=load_font(16))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(OUT))
    print(f"✅ 輸出：{OUT}")


if __name__ == "__main__":
    main()
