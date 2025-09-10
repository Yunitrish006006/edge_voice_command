#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
簡化版 ESP32 音訊數據接收器
專門接收和顯示ESP32的音訊MQTT數據
"""

import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import json
import time
from datetime import datetime
from collections import deque

class SimpleAudioReceiver:
    """簡單的音訊數據接收器"""
    
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # 數據儲存
        self.volume_data = deque(maxlen=100)
        self.frequency_data = deque(maxlen=50)
        self.timestamps = deque(maxlen=100)
        self.voice_detections = []
        
        # 統計
        self.message_count = 0
        self.voice_count = 0
        
        # MQTT 設定
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        
        # 設定圖表
        self.setup_plots()
        
    def setup_plots(self):
        """設定圖表"""
        plt.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(2, 2, figsize=(12, 8))
        self.fig.suptitle('ESP32 音訊數據即時監控', fontsize=14, fontweight='bold')
        
        # 1. 音量圖
        self.ax1.set_title('即時音量')
        self.ax1.set_ylabel('音量 (RMS)')
        self.ax1.set_xlabel('時間')
        self.ax1.grid(True, alpha=0.3)
        self.volume_line, = self.ax1.plot([], [], 'b-', linewidth=2, label='音量')
        self.ax1.axhline(y=0.1, color='r', linestyle='--', label='閾值', alpha=0.7)
        self.ax1.legend()
        
        # 2. 頻率圖
        self.ax2.set_title('頻率分析')
        self.ax2.set_ylabel('振幅')
        self.ax2.set_xlabel('頻率段')
        self.ax2.grid(True, alpha=0.3)
        self.freq_bars = self.ax2.bar(range(10), [0]*10, alpha=0.7, color='green')
        
        # 3. 音量統計
        self.ax3.set_title('音量分佈')
        self.ax3.set_ylabel('次數')
        self.ax3.set_xlabel('音量範圍')
        self.ax3.grid(True, alpha=0.3)
        
        # 4. 語音檢測
        self.ax4.set_title('語音檢測記錄')
        self.ax4.set_ylabel('檢測次數')
        self.ax4.set_xlabel('時間')
        self.ax4.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """連接回調"""
        if reason_code == 0:
            self.connected = True
            print("✅ 已連接到 MQTT Broker")
            
            # 訂閱音訊相關主題
            topics = [
                "esp32/audio/volume",
                "esp32/audio/frequencies", 
                "esp32/voice/detected",
                "esp32/audio/+",
                "esp32/voice/+"
            ]
            
            for topic in topics:
                client.subscribe(topic)
                print(f"📡 已訂閱: {topic}")
                
        else:
            print(f"❌ 連接失敗: {reason_code}")
    
    def on_message(self, client, userdata, msg):
        """訊息回調"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        timestamp = time.time()
        
        self.message_count += 1
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {topic}: {payload}")
        
        # 處理不同類型的數據
        if topic == "esp32/audio/volume":
            self.process_volume(payload, timestamp)
        elif topic == "esp32/audio/frequencies":
            self.process_frequencies(payload, timestamp)
        elif topic == "esp32/voice/detected":
            self.process_voice_detection(payload, timestamp)
    
    def process_volume(self, payload, timestamp):
        """處理音量數據"""
        try:
            volume = float(payload)
            self.volume_data.append(volume)
            self.timestamps.append(timestamp)
            print(f"🔊 音量: {volume:.3f}")
        except ValueError:
            print(f"⚠️ 無效音量: {payload}")
    
    def process_frequencies(self, payload, timestamp):
        """處理頻率數據"""
        try:
            if ',' in payload:
                frequencies = [float(f.strip()) for f in payload.split(',')]
            else:
                frequencies = json.loads(payload)
            
            # 只保留前10個頻率
            self.frequency_data.append(frequencies[:10])
            print(f"🎵 頻率: {frequencies[:3]}")
            
        except (ValueError, json.JSONDecodeError):
            print(f"⚠️ 無效頻率: {payload}")
    
    def process_voice_detection(self, payload, timestamp):
        """處理語音檢測"""
        if payload.lower() in ['true', '1', 'detected']:
            self.voice_count += 1
            self.voice_detections.append(timestamp)
            print(f"🗣️ 語音檢測 #{self.voice_count}")
    
    def update_plots(self, frame):
        """更新圖表"""
        # 更新音量圖
        if len(self.volume_data) > 1:
            x_data = list(range(len(self.volume_data)))
            y_data = list(self.volume_data)
            
            self.volume_line.set_data(x_data, y_data)
            self.ax1.relim()
            self.ax1.autoscale_view()
            
            # 設定Y軸範圍
            if y_data:
                max_vol = max(y_data)
                self.ax1.set_ylim(0, max(0.5, max_vol * 1.1))
        
        # 更新頻率圖
        if self.frequency_data:
            latest_freq = list(self.frequency_data)[-1]
            
            # 確保有10個數據
            while len(latest_freq) < 10:
                latest_freq.append(0)
            
            for i, bar in enumerate(self.freq_bars):
                if i < len(latest_freq):
                    bar.set_height(latest_freq[i])
            
            if latest_freq:
                max_freq = max(latest_freq)
                self.ax2.set_ylim(0, max(100, max_freq * 1.1))
        
        # 更新音量分佈直方圖
        if len(self.volume_data) > 10:
            self.ax3.clear()
            self.ax3.hist(list(self.volume_data), bins=15, alpha=0.7, 
                         color='blue', edgecolor='black')
            self.ax3.set_title('音量分佈')
            self.ax3.set_ylabel('次數')
            self.ax3.set_xlabel('音量範圍')
            self.ax3.grid(True, alpha=0.3)
        
        # 更新語音檢測圖
        if self.voice_detections:
            # 顯示最近的語音檢測
            recent_detections = self.voice_detections[-20:]  # 最近20次
            x_data = list(range(len(recent_detections)))
            y_data = [1] * len(recent_detections)
            
            self.ax4.clear()
            self.ax4.scatter(x_data, y_data, c='red', s=50, alpha=0.7)
            self.ax4.set_title(f'語音檢測記錄 (總共: {self.voice_count})')
            self.ax4.set_ylabel('檢測事件')
            self.ax4.set_xlabel('檢測序號')
            self.ax4.grid(True, alpha=0.3)
            
            if x_data:
                self.ax4.set_xlim(-1, max(10, max(x_data) + 1))
                self.ax4.set_ylim(0.5, 1.5)
        
        # 更新標題顯示統計
        current_time = datetime.now().strftime('%H:%M:%S')
        title = f'ESP32 音訊數據即時監控 - {current_time} | 訊息: {self.message_count} | 語音: {self.voice_count}'
        self.fig.suptitle(title, fontsize=12)
        
        return []
    
    def connect(self):
        """連接到 MQTT"""
        try:
            print(f"🔗 正在連接到 {self.broker_host}:{self.broker_port}")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False
    
    def disconnect(self):
        """斷開連接"""
        self.client.loop_stop()
        self.client.disconnect()
        print("🔌 已斷開連接")
    
    def send_command(self, command):
        """發送控制指令"""
        if self.connected:
            self.client.publish("esp32/command", command)
            print(f"📤 發送指令: {command}")
        else:
            print("❌ 未連接，無法發送指令")
    
    def save_data(self, filename=None):
        """儲存數據"""
        if filename is None:
            filename = f"esp32_audio_{int(time.time())}.json"
        
        data = {
            'volume_data': list(self.volume_data),
            'frequency_data': [list(freq) for freq in self.frequency_data],
            'timestamps': list(self.timestamps),
            'voice_detections': self.voice_detections,
            'message_count': self.message_count,
            'voice_count': self.voice_count,
            'saved_at': datetime.now().isoformat()
        }
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            print(f"💾 數據已儲存到 {filename}")
        except Exception as e:
            print(f"❌ 儲存失敗: {e}")
    
    def run(self):
        """啟動監控"""
        if not self.connect():
            return
        
        try:
            # 啟動動畫
            ani = animation.FuncAnimation(
                self.fig, self.update_plots, interval=1000, blit=False
            )
            
            print("📊 圖表視窗已開啟，按 Ctrl+C 停止監控")
            print("💡 可用指令:")
            print("   - 在終端輸入 's' 儲存數據")
            print("   - 在終端輸入 'beep' 測試ESP32喇叭")
            print("   - 在終端輸入 'status' 查看ESP32狀態")
            
            plt.show()
            
        except KeyboardInterrupt:
            print("\\n🛑 正在停止監控...")
        finally:
            self.save_data()
            self.disconnect()

def main():
    """主程式"""
    print("🎵 ESP32 音訊數據接收器")
    print("=" * 30)
    
    # 創建接收器 (使用你的 MQTT broker 地址)
    receiver = SimpleAudioReceiver("localhost", 1883)
    
    # 啟動監控
    receiver.run()

if __name__ == "__main__":
    main()
