#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 音訊資料接收器
專門接收ESP32透過MQTT傳送的音訊資料塊，並重組成完整的音訊檔案
"""

import paho.mqtt.client as mqtt
import time
import json
import os
import wave
import struct
from datetime import datetime
from collections import defaultdict
from config import MQTTConfig

class AudioDataReceiver:
    """音訊資料接收器"""
    
    def __init__(self):
        # 載入配置
        self.config = MQTTConfig()
        self.broker_host, self.broker_port = self.config.get_broker_info()
        
        # 音訊資料重組
        self.audio_chunks = defaultdict(dict)  # timestamp: {chunk_index: data}
        self.audio_headers = {}  # timestamp: header_info
        self.completed_audio = {}  # timestamp: complete_data
        
        # 統計
        self.total_chunks_received = 0
        self.total_audio_files = 0
        
        # 設定MQTT客戶端
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION2)
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.connected = False
        
        # 創建輸出目錄
        self.output_dir = "received_audio"
        os.makedirs(self.output_dir, exist_ok=True)
        
        print(f"🎵 ESP32 音訊資料接收器啟動")
        print(f"📁 音訊檔案將儲存到: {self.output_dir}")
        print(f"🌐 MQTT Broker: {self.broker_host}:{self.broker_port}")
    
    def on_connect(self, client, userdata, flags, reason_code, properties):
        """MQTT連接回調"""
        if reason_code == 0:
            self.connected = True
            print("✅ MQTT連接成功")
            
            # 訂閱音訊資料主題
            topics = self.config.get_topics()
            audio_prefix = topics.get('audio_prefix', 'esp32/audio')
            client.subscribe(f"{audio_prefix}/+/+")  # 格式: <prefix>/timestamp/chunk_index
            client.subscribe(f"{audio_prefix}/info")  # 訂閱資訊通知
            
            print("📡 已訂閱音訊資料主題")
        else:
            print(f"❌ MQTT連接失敗: {reason_code}")
    
    def on_message(self, client, userdata, msg):
        """MQTT訊息回調"""
        topic = msg.topic
        payload = msg.payload
        
        try:
            topics = self.config.get_topics()
            audio_prefix = topics.get('audio_prefix', 'esp32/audio')
            if topic == f"{audio_prefix}/info":
                # 完成通知
                self.handle_completion_message(payload)
            elif topic.startswith(f"{audio_prefix}/"):
                # 音訊資料塊
                self.handle_audio_chunk(topic, payload)
        except Exception as e:
            print(f"❌ 處理訊息時發生錯誤: {e}")
    
    def handle_audio_chunk(self, topic, payload):
        """處理音訊資料塊"""
        # 解析主題格式: <audio_prefix>/timestamp/chunk_index（如 esp32/audio/1690000000000/12）
        parts = topic.split('/')
        # 預期 parts: [esp32, audio, timestamp, chunk_index]
        if len(parts) >= 4:
            try:
                timestamp = int(parts[2])
                chunk_index = int(parts[3])
            except Exception:
                print(f"⚠️ 主題解析失敗: {topic}")
                return
            
            # 儲存音訊塊
            if timestamp not in self.audio_chunks:
                self.audio_chunks[timestamp] = {}
                print(f"📦 開始接收時間戳 {timestamp} 的音訊資料")
            
            self.audio_chunks[timestamp][chunk_index] = payload
            self.total_chunks_received += 1

            print(f"📥 收到音訊塊: 時間戳={timestamp}, 塊={chunk_index}, 大小={len(payload)} 位元組")
    
    def handle_completion_message(self, payload):
        """處理完成通知訊息"""
        try:
            message = payload.decode('utf-8')
            # 新格式: timestamp:size:success_count:total_chunks
            parts = message.split(':')
            if len(parts) >= 4:
                timestamp = int(parts[0])
                expected_size = int(parts[1])
                success_count = int(parts[2])
                total_chunks = int(parts[3])
                
                print(f"� 收到完成通知: 時間戳={timestamp}, 大小={expected_size}, 成功={success_count}/{total_chunks}")
                
                # 更新標頭資訊
                self.audio_headers[timestamp] = {
                    'total_size': expected_size,
                    'total_chunks': total_chunks,
                    'success_count': success_count,
                    'received_chunks': len(self.audio_chunks.get(timestamp, {}))
                }
                
                # 組裝音訊
                self.assemble_audio(timestamp, expected_size)
                
        except Exception as e:
            print(f"❌ 處理完成訊息時發生錯誤: {e}")
    
    def check_completion(self):
        """檢查是否有完整的音訊資料可以組裝"""
        for timestamp, header_info in list(self.audio_headers.items()):
            if header_info['received_chunks'] >= header_info['total_chunks']:
                self.assemble_audio(timestamp, header_info['total_size'])
    
    def assemble_audio(self, timestamp, expected_size):
        """組裝完整的音訊資料"""
        if timestamp not in self.audio_chunks:
            print(f"⚠️ 時間戳 {timestamp} 沒有音訊塊資料")
            return
        
        # 按順序組裝音訊塊
        chunks = self.audio_chunks[timestamp]
        chunk_indices = sorted(chunks.keys())
        
        assembled_data = b''
        for index in chunk_indices:
            assembled_data += chunks[index]
        
        actual_size = len(assembled_data)
        print(f"🔧 組裝音訊: 時間戳={timestamp}, 實際大小={actual_size}, 預期大小={expected_size}")
        
        if actual_size > 0:
            # 儲存音訊檔案
            self.save_audio_file(timestamp, assembled_data)
            
            # 清理已處理的資料
            del self.audio_chunks[timestamp]
            if timestamp in self.audio_headers:
                del self.audio_headers[timestamp]
        else:
            print(f"⚠️ 組裝的音訊資料為空")
    
    def save_audio_file(self, timestamp, audio_data):
        """儲存音訊檔案"""
        try:
            # 轉換時間戳為可讀時間
            dt = datetime.fromtimestamp(timestamp / 1000.0)  # ESP32使用毫秒
            time_str = dt.strftime("%Y%m%d_%H%M%S_%f")[:-3]  # 包含毫秒
            
            # 原始音訊資料檔案
            raw_filename = f"audio_{time_str}.raw"
            raw_path = os.path.join(self.output_dir, raw_filename)
            
            with open(raw_path, 'wb') as f:
                f.write(audio_data)
            
            print(f"💾 原始音訊已儲存: {raw_filename} ({len(audio_data)} 位元組)")
            
            # 嘗試轉換為WAV格式
            try:
                wav_filename = f"audio_{time_str}.wav"
                wav_path = os.path.join(self.output_dir, wav_filename)
                
                # ESP32 I2S 參數: 16kHz, 16-bit, 單聲道
                sample_rate = 16000
                sample_width = 2  # 16-bit = 2 bytes
                channels = 1
                
                with wave.open(wav_path, 'wb') as wav_file:
                    wav_file.setnchannels(channels)
                    wav_file.setsampwidth(sample_width)
                    wav_file.setframerate(sample_rate)
                    wav_file.writeframes(audio_data)
                
                print(f"🎵 WAV檔案已儲存: {wav_filename}")
                
                # 計算音訊時長
                num_samples = len(audio_data) // sample_width
                duration = num_samples / sample_rate
                print(f"⏱️ 音訊時長: {duration:.2f} 秒")
                
            except Exception as e:
                print(f"⚠️ WAV轉換失敗: {e}")
            
            self.total_audio_files += 1
            
        except Exception as e:
            print(f"❌ 儲存音訊檔案時發生錯誤: {e}")
    
    def print_status(self):
        """顯示狀態資訊"""
        print(f"\n📊 狀態統計:")
        print(f"   MQTT連接: {'✅ 已連接' if self.connected else '❌ 斷線'}")
        print(f"   收到音訊塊: {self.total_chunks_received}")
        print(f"   完成音訊檔案: {self.total_audio_files}")
        print(f"   等待組裝: {len(self.audio_headers)} 個")
        
        if self.audio_headers:
            print(f"   等待中的時間戳:")
            for timestamp, info in self.audio_headers.items():
                dt = datetime.fromtimestamp(timestamp / 1000.0)
                progress = info['received_chunks'] / info['total_chunks'] * 100
                print(f"     {dt.strftime('%H:%M:%S')}: {progress:.1f}% ({info['received_chunks']}/{info['total_chunks']})")
    
    def connect(self):
        """連接到MQTT broker"""
        try:
            print(f"🔌 連接到 MQTT Broker...")
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"❌ 連接失敗: {e}")
            return False
    
    def disconnect(self):
        """斷開MQTT連接"""
        self.client.loop_stop()
        self.client.disconnect()
        print("🔌 MQTT連接已斷開")
    
    def run(self):
        """執行接收器"""
        if not self.connect():
            return
        
        print(f"\n📡 開始監聽音訊資料...")
        print(f"💡 發送 'start_audio_data' 指令到 ESP32 開始收集音訊資料")
        print(f"💡 按 Ctrl+C 停止接收")
        
        try:
            last_status_time = time.time()
            while True:
                time.sleep(1)
                
                # 每10秒顯示一次狀態
                current_time = time.time()
                if current_time - last_status_time >= 10:
                    self.print_status()
                    last_status_time = current_time
                    
        except KeyboardInterrupt:
            print(f"\n🛑 使用者中斷，正在停止...")
            
        finally:
            self.print_status()
            self.disconnect()

def main():
    """主程式"""
    receiver = AudioDataReceiver()
    receiver.run()

if __name__ == "__main__":
    main()
