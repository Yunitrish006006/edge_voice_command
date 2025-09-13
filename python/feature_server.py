#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最小特徵接收與回覆伺服器
- 訂閱: esp32/feat/{device}/{session}/{idx} 與 esp32/feat/info
- 聚合每個 session 的幀，並回覆簡單推論結果至 esp32/infer/{device}
- 僅為 Demo 用，不執行真實模型推論
"""

import base64
import json
import queue
import random
import threading
import time
from collections import defaultdict

import paho.mqtt.client as mqtt

from config import MQTTConfig


class FeatureServer:
    def __init__(self):
        self.cfg = MQTTConfig()
        self.host, self.port = self.cfg.get_broker_info()
        self.topics = self.cfg.get_topics()
        self.server_cfg = self.cfg.get_server_config()

        # session → accumulator（不留原始資料，降低記憶體）
        # 格式：{"sum": float, "count": int, "dtype": "u8"|"f32"}
        self.session_acc = defaultdict(lambda: {"sum": 0.0, "count": 0, "dtype": "u8"})
        # session meta: expected frames (if announced)
        self.session_meta = {}

        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def run(self):
        print(f"🌐 連接 MQTT: {self.host}:{self.port}")
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_forever()

    # MQTT callbacks
    def on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("✅ 連接成功。訂閱特徵主題…")
            feat_prefix = self.topics.get('feature_prefix', 'esp32/feat')
            client.subscribe(f"{feat_prefix}/+/+/+")  # device/session/idx
            client.subscribe(f"{feat_prefix}/info")
        else:
            print(f"❌ 連接失敗: {reason_code}")

    def on_message(self, client, userdata, msg):
        topic = msg.topic
        try:
            feat_prefix = self.topics.get('feature_prefix', 'esp32/feat')
            if topic == f"{feat_prefix}/info":
                self._handle_info(msg.payload)
            elif topic.startswith(f"{feat_prefix}/"):
                self._handle_feature(topic, msg.payload)
        except Exception as e:
            print(f"⚠️ 處理訊息錯誤: {e}")

    # Handlers
    def _handle_info(self, payload: bytes):
        try:
            info = json.loads(payload.decode('utf-8'))
            device = info.get('device')
            session = info.get('session')
            frames = int(info.get('frames', 0))
            if device and session:
                self.session_meta[(device, session)] = {"frames": frames}
                print(f"ℹ️ 會話資訊 device={device} session={session} frames={frames}")
        except Exception as e:
            print(f"⚠️ 解析 info 失敗: {e}")

    def _handle_feature(self, topic: str, payload: bytes):
        parts = topic.split('/')
        # {feat_prefix}/{device}/{session}/{idx}
        device, session, idx = parts[-3], parts[-2], int(parts[-1])
        obj = json.loads(payload.decode('utf-8'))
        # 解析與累積
        values, dtype = self._decode_feature_values(obj)
        acc = self.session_acc[(device, session)]
        acc["sum"] += sum(values)
        acc["count"] += len(values)
        acc["dtype"] = dtype
        expect = self.session_meta.get((device, session), {}).get('frames', 0)
        # 使用 frames 計數（而非值數）作為是否決策的門檻
        frame_count = acc.get("frames", 0) + 1
        acc["frames"] = frame_count
        shape = obj.get('shape')
        print(f"📥 {device}/{session} 收到幀#{idx}（幀 {frame_count}/{expect}），shape={shape}")

        # Demo 策略：收到 N 幀就回覆一次結果
        N = int(self.server_cfg.get('frames_to_decide', 6))
        if frame_count >= N or (expect and frame_count >= expect):
            self._reply_inference(device, session)
            # 清空此 session（單次決策）
            if (device, session) in self.session_acc:
                del self.session_acc[(device, session)]
            if (device, session) in self.session_meta:
                del self.session_meta[(device, session)]

    def _reply_inference(self, device: str, session: str):
        # 簡單規則：以整段均值做活動度（u8 → 0..1；f32 假定 0..1）
        acc = self.session_acc.get((device, session), {"sum": 0.0, "count": 1, "dtype": "u8", "frames": 0})
        mean_val = (acc["sum"] / max(1, acc["count"]))
        if acc.get("dtype") == "u8":
            score = mean_val / 255.0
        else:
            score = float(mean_val)
        thr = float(self.cfg.config.get('server', 'energy_threshold', fallback='0.6'))
        if score >= thr:
            label = "yes"
            conf = round(min(0.99, 0.5 + 0.5 * (score - thr) / max(1e-6, 1.0 - thr)), 2)
        else:
            label = "no"
            conf = round(max(0.51, 0.9 * (1 - (thr - score))), 2)
        frames = int(acc.get("frames", 0))
        payload = {
            "ts": int(time.time() * 1000),
            "session": session,
            "frames": frames,
            "result": label,
            "conf": conf,
            "score": round(score, 3)
        }
        infer_prefix = self.topics.get('infer_prefix', 'esp32/infer')
        topic = f"{infer_prefix}/{device}"
        self.client.publish(topic, json.dumps(payload).encode('utf-8'), qos=0, retain=False)
        print(f"✅ 回覆推論 {payload} → {topic}")

    def _decode_feature_values(self, obj):
        """將一幀特徵 JSON 還原為數值列表與資料型別標記。"""
        b64 = obj.get('data', '')
        q = obj.get('q', 'u8')
        raw = base64.b64decode(b64) if b64 else b''
        shape = obj.get('shape', [1, 0])
        count = int(shape[0]) * int(shape[1]) if shape and len(shape) == 2 else len(raw)
        values = []
        if q == 'u8':
            # 直接解析為 0..255
            values = list(raw[:count])
            dtype = 'u8'
        else:
            # 以 little-endian float32 解析
            import struct
            values = list(struct.unpack('<' + 'f' * (len(raw) // 4), raw))
            # 截斷到 shape 對應長度
            if len(values) > count:
                values = values[:count]
            dtype = 'f32'
        return values, dtype


if __name__ == "__main__":
    FeatureServer().run()
