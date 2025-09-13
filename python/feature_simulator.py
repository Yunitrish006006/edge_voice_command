#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
特徵模擬上傳腳本
- 目的：模擬 ESP32 上傳 log‑Mel/MFCC 特徵到 MQTT Broker，方便端‑雲資料流 Demo。
- 相依：paho-mqtt（已在 requirements.txt）
"""

import base64
import json
import os
import random
import time
from datetime import datetime

import paho.mqtt.client as mqtt

from config import MQTTConfig


def now_ms() -> int:
    return int(time.time() * 1000)


def make_random_feature(num_frames=10, num_bins=40, quant="u8"):
    """產生隨機特徵（用於訊息格式/通路測試），不依賴 numpy。"""
    if quant == "u8":
        # 逐幀產生 0..255 的整數
        frames = []
        for _ in range(num_frames):
            frames.append(bytes(random.getrandbits(8) for _ in range(num_bins)))
        # 合併為連續位元組，並記錄形狀
        raw = b"".join(frames)
        dtype = "u8"
    else:
        # 以 32-bit float 模擬（0..1），以 struct 打包
        import struct
        buf = []
        for _ in range(num_frames * num_bins):
            buf.append(struct.pack('<f', random.random()))
        raw = b"".join(buf)
        dtype = "f32"
    return raw, (num_frames, num_bins), dtype


def encode_payload(raw, shape, sr=16000, feat="logmel", win_ms=25, hop_ms=10, quant="u8"):
    data = base64.b64encode(raw).decode("ascii")
    payload = {
        "ts": now_ms(),
        "sr": sr,
        "feat": feat,
        "shape": [int(shape[0]), int(shape[1])],
        "win_ms": win_ms,
        "hop_ms": hop_ms,
        "q": quant,
        "data": data,
    }
    return payload


def main():
    cfg = MQTTConfig()
    host, port = cfg.get_broker_info()
    topics = cfg.get_topics()

    device_id = os.environ.get("DEVICE_ID", f"esp32s3_{random.randint(1000,9999)}")
    session_id = str(now_ms())
    frames = int(os.environ.get("FRAMES", "12"))
    bins = int(os.environ.get("BINS", "40"))
    feat_type = os.environ.get("FEAT", "logmel")
    quant = os.environ.get("QUANT", "u8")  # u8/f32
    interval_ms = int(os.environ.get("INTERVAL_MS", "50"))

    feat_prefix = topics.get('feature_prefix', 'esp32/feat')
    info_topic = f"{feat_prefix}/info"

    print(f"🌐 MQTT {host}:{port}")
    print(f"📦 發送主題前綴: {feat_prefix}/{device_id}/{session_id}")
    print(f"🔧 參數: frames={frames}, bins={bins}, feat={feat_type}, q={quant}")

    client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
    client.connect(host, port, keepalive=60)
    client.loop_start()

    try:
        for idx in range(frames):
            raw, shape, dtype = make_random_feature(num_frames=1, num_bins=bins, quant=quant)
            payload = encode_payload(raw, shape, feat=feat_type, quant=dtype)
            topic = f"{feat_prefix}/{device_id}/{session_id}/{idx}"
            client.publish(topic, json.dumps(payload).encode("utf-8"), qos=0, retain=False)
            print(f"📤 發送 frame {idx} → {topic}")
            time.sleep(interval_ms / 1000.0)

        # 發送一個會話完成通知（可選）
        info = {
            "device": device_id,
            "session": session_id,
            "frames": frames,
            "ts": now_ms(),
        }
        client.publish(info_topic, json.dumps(info).encode("utf-8"), qos=0, retain=False)
        print(f"✅ 會話完成通知 → {info_topic}")

    finally:
        time.sleep(0.2)
        client.loop_stop()
        client.disconnect()
        print("👋 結束")


if __name__ == "__main__":
    main()
