#!/usr/bin/env python3
"""
簡單的 MQTT Broker 用於接收 ESP32 語音命令
"""

import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime

class MQTTBroker:
    def __init__(self, host="localhost", port=1883):
        self.host = host
        self.port = port
        self.client = mqtt.Client()
        self.setup_callbacks()
        
    def setup_callbacks(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print(f"[{self.get_timestamp()}] 連接成功到 MQTT Broker")
            # 訂閱 ESP32 的主題
            client.subscribe("esp32/voice_command")
            client.subscribe("esp32/+")  # 訂閱所有 esp32 相關主題
            print(f"[{self.get_timestamp()}] 已訂閱主題: esp32/voice_command")
        else:
            print(f"[{self.get_timestamp()}] 連接失敗，錯誤代碼: {rc}")
            
    def on_message(self, client, userdata, msg):
        timestamp = self.get_timestamp()
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        print(f"\n{'='*50}")
        print(f"[{timestamp}] 收到訊息")
        print(f"主題: {topic}")
        print(f"內容: {payload}")
        print(f"{'='*50}\n")
        
        # 可以在這裡添加處理邏輯
        self.process_message(topic, payload)
        
    def on_disconnect(self, client, userdata, rc):
        print(f"[{self.get_timestamp()}] 與 MQTT Broker 斷線")
        
    def process_message(self, topic, payload):
        """處理收到的訊息"""
        if topic == "esp32/voice_command":
            print(f"[處理] 語音命令: {payload}")
            # 在這裡可以添加語音命令的處理邏輯
            
    def get_timestamp(self):
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
    def start(self):
        try:
            print(f"[{self.get_timestamp()}] 啟動 MQTT 客戶端...")
            print(f"[{self.get_timestamp()}] 連接到: {self.host}:{self.port}")
            
            self.client.connect(self.host, self.port, 60)
            self.client.loop_forever()
            
        except KeyboardInterrupt:
            print(f"\n[{self.get_timestamp()}] 收到中斷信號，正在關閉...")
            self.client.disconnect()
        except Exception as e:
            print(f"[{self.get_timestamp()}] 錯誤: {e}")

if __name__ == "__main__":
    # 使用免費的 HiveMQ broker
    broker = MQTTBroker("broker.hivemq.com", 1883)
    
    print("MQTT 語音命令接收器")
    print("==================")
    print("按 Ctrl+C 停止程式")
    print()
    
    broker.start()
