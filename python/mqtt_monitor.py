#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
獨立的 MQTT 監控客戶端
專門負責訂閱和顯示 MQTT 訊息
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import paho.mqtt.client as mqtt
import threading
import queue
import time
from datetime import datetime
from config import MQTTConfig

class MQTTMonitorClient:
    """MQTT 監控客戶端"""
    
    def __init__(self):
        # 主視窗
        self.root = tk.Tk()
        self.root.title("🔍 MQTT 訊息監控器")
        self.root.geometry("900x700")
        
        # MQTT 設定
        self.config = MQTTConfig()
        self.broker_host, self.broker_port = self.config.get_broker_info()
        self.mqtt_client = None
        self.connected = False
        self.subscribed_topics = set()
        
        # 訊息佇列和統計
        self.message_queue = queue.Queue()
        self.message_count = 0
        
        # Debug 模式
        self.debug_mode = tk.BooleanVar()
        
        # 建立 UI
        self._setup_ui()
        self._setup_mqtt()
        
        # 啟動訊息處理
        self._start_message_processing()
        
        # 視窗關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_ui(self):
        """建立使用者介面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(main_frame, text="🔍 MQTT 訊息監控器", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 連接狀態框架
        status_frame = ttk.LabelFrame(main_frame, text="連接狀態", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 狀態指示器
        self.status_label = ttk.Label(status_frame, text="狀態: 未連接", 
                                     foreground="red", font=("Arial", 10, "bold"))
        self.status_label.pack(side=tk.LEFT)
        
        # 連接按鈕
        self.connect_btn = ttk.Button(status_frame, text="連接", 
                                     command=self._toggle_connection)
        self.connect_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 服務器資訊
        server_label = ttk.Label(status_frame, 
                                text=f"🌐 服務器: {self.broker_host}:{self.broker_port}")
        server_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # 主題管理框架
        topic_frame = ttk.LabelFrame(main_frame, text="主題管理", padding="5")
        topic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 主題輸入
        ttk.Label(topic_frame, text="訂閱主題:").pack(side=tk.LEFT)
        self.topic_entry = ttk.Entry(topic_frame, width=30)
        self.topic_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.topic_entry.insert(0, "esp32/+")
        
        # 訂閱按鈕
        subscribe_btn = ttk.Button(topic_frame, text="訂閱", 
                                  command=self._subscribe_topic)
        subscribe_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 預設主題按鈕
        preset_frame = ttk.Frame(topic_frame)
        preset_frame.pack(side=tk.LEFT, padx=(10, 0))
        
        presets = [("ESP32", "esp32/+"), ("測試", "test/+"), ("全部", "#")]
        for name, topic in presets:
            btn = ttk.Button(preset_frame, text=name, width=8,
                           command=lambda t=topic: self._quick_subscribe(t))
            btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 已訂閱主題顯示
        subscribed_frame = ttk.Frame(main_frame)
        subscribed_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(subscribed_frame, text="已訂閱主題:").pack(side=tk.LEFT)
        self.subscribed_label = ttk.Label(subscribed_frame, text="無", 
                                         foreground="gray")
        self.subscribed_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 訊息顯示區域
        message_frame = ttk.LabelFrame(main_frame, text="MQTT 訊息", padding="5")
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 訊息文字區域
        self.message_text = scrolledtext.ScrolledText(
            message_frame, 
            wrap=tk.WORD, 
            height=20,
            font=("Consolas", 10)
        )
        self.message_text.pack(fill=tk.BOTH, expand=True)
        
        # 底部控制框架
        control_frame = ttk.Frame(main_frame)
        control_frame.pack(fill=tk.X)
        
        # 統計資訊
        self.stats_label = ttk.Label(control_frame, text="訊息數: 0")
        self.stats_label.pack(side=tk.LEFT)
        
        # Debug 模式
        debug_check = ttk.Checkbutton(control_frame, text="Debug 模式", 
                                     variable=self.debug_mode)
        debug_check.pack(side=tk.LEFT, padx=(20, 0))
        
        # 清除按鈕
        clear_btn = ttk.Button(control_frame, text="清除訊息", 
                              command=self._clear_messages)
        clear_btn.pack(side=tk.RIGHT)
    
    def _setup_mqtt(self):
        """設定 MQTT 客戶端"""
        # 創建唯一客戶端ID
        client_id = f"Monitor_{int(time.time())}_{id(self)}"
        
        self.mqtt_client = mqtt.Client(
            client_id=client_id, 
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        # 設定回調函數
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
        
        if self.debug_mode.get():
            print(f"[DEBUG] 客戶端ID: {client_id}")
    
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """MQTT 連接回調"""
        if self.debug_mode.get():
            print(f"[DEBUG] 連接結果: {reason_code}")
        
        if reason_code == 0:
            self.connected = True
            self.message_queue.put(("status", "connected"))
            
            # 自動訂閱預設主題
            default_topic = self.topic_entry.get()
            if default_topic:
                self._subscribe_to_topic(default_topic)
        else:
            self.message_queue.put(("status", f"error_{reason_code}"))
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息接收回調"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        
        # 加入訊息佇列
        self.message_queue.put(("message", {
            "timestamp": timestamp,
            "topic": topic,
            "payload": payload
        }))
        
        if self.debug_mode.get():
            print(f"[DEBUG] 收到訊息: {topic} -> {payload}")
    
    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """MQTT 斷線回調"""
        if self.debug_mode.get():
            print(f"[DEBUG] 斷線: {reason_code}")
        
        self.connected = False
        self.subscribed_topics.clear()
        self.message_queue.put(("status", "disconnected"))
    
    def _start_message_processing(self):
        """啟動訊息處理線程"""
        def process_messages():
            while True:
                try:
                    msg_type, data = self.message_queue.get(timeout=0.1)
                    
                    if msg_type == "status":
                        self._update_status(data)
                    elif msg_type == "message":
                        self._display_message(data)
                    elif msg_type == "topics":
                        self._update_subscribed_topics(data)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    if self.debug_mode.get():
                        print(f"[DEBUG] 訊息處理錯誤: {e}")
        
        msg_thread = threading.Thread(target=process_messages, daemon=True)
        msg_thread.start()
    
    def _update_status(self, status):
        """更新連接狀態"""
        if status == "connected":
            self.status_label.config(text="狀態: 已連接", foreground="green")
            self.connect_btn.config(text="斷開")
        elif status == "disconnected":
            self.status_label.config(text="狀態: 已斷開", foreground="red")
            self.connect_btn.config(text="連接")
        else:
            self.status_label.config(text=f"狀態: 錯誤 {status}", foreground="orange")
            self.connect_btn.config(text="連接")
    
    def _display_message(self, msg_data):
        """顯示 MQTT 訊息"""
        timestamp = msg_data["timestamp"]
        topic = msg_data["topic"]
        payload = msg_data["payload"]
        
        # 格式化訊息
        message_line = f"[{timestamp}] 📢 {topic}: {payload}\n"
        
        # 顯示在文字區域
        self.message_text.insert(tk.END, message_line)
        self.message_text.see(tk.END)
        
        # 更新統計
        self.message_count += 1
        self.stats_label.config(text=f"訊息數: {self.message_count}")
        
        # 限制訊息數量
        if self.message_count > 1000:
            # 刪除前面的訊息
            lines = self.message_text.get("1.0", tk.END).split('\n')
            if len(lines) > 500:
                new_content = '\n'.join(lines[-500:])
                self.message_text.delete("1.0", tk.END)
                self.message_text.insert("1.0", new_content)
    
    def _update_subscribed_topics(self, topics):
        """更新已訂閱主題顯示"""
        if topics:
            topics_text = ", ".join(topics)
            self.subscribed_label.config(text=topics_text, foreground="blue")
        else:
            self.subscribed_label.config(text="無", foreground="gray")
    
    def _toggle_connection(self):
        """切換連接狀態"""
        if self.connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """連接到 MQTT Broker"""
        try:
            if self.debug_mode.get():
                print(f"[DEBUG] 嘗試連接到 {self.broker_host}:{self.broker_port}")
            
            self.mqtt_client.connect(
                self.broker_host, 
                self.broker_port, 
                60
            )
            self.mqtt_client.loop_start()
            
            self._add_message("🔗 正在連接...")
            
        except Exception as e:
            messagebox.showerror("連接錯誤", f"無法連接到 MQTT Broker: {e}")
            if self.debug_mode.get():
                print(f"[DEBUG] 連接錯誤: {e}")
    
    def _disconnect(self):
        """斷開 MQTT 連接"""
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self._add_message("🔌 已斷開連接")
            
        except Exception as e:
            if self.debug_mode.get():
                print(f"[DEBUG] 斷開錯誤: {e}")
    
    def _subscribe_topic(self):
        """訂閱主題"""
        topic = self.topic_entry.get().strip()
        if topic and self.connected:
            self._subscribe_to_topic(topic)
    
    def _quick_subscribe(self, topic):
        """快速訂閱預設主題"""
        self.topic_entry.delete(0, tk.END)
        self.topic_entry.insert(0, topic)
        if self.connected:
            self._subscribe_to_topic(topic)
    
    def _subscribe_to_topic(self, topic):
        """訂閱指定主題"""
        try:
            self.mqtt_client.subscribe(topic)
            self.subscribed_topics.add(topic)
            self.message_queue.put(("topics", list(self.subscribed_topics)))
            self._add_message(f"📡 已訂閱: {topic}")
            
            if self.debug_mode.get():
                print(f"[DEBUG] 訂閱主題: {topic}")
                
        except Exception as e:
            messagebox.showerror("訂閱錯誤", f"無法訂閱主題: {e}")
    
    def _add_message(self, message):
        """添加系統訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message_line = f"[{timestamp}] ℹ️ {message}\n"
        self.message_text.insert(tk.END, message_line)
        self.message_text.see(tk.END)
    
    def _clear_messages(self):
        """清除所有訊息"""
        self.message_text.delete("1.0", tk.END)
        self.message_count = 0
        self.stats_label.config(text="訊息數: 0")
        self._add_message("🧹 訊息已清除")
    
    def _on_closing(self):
        """視窗關閉處理"""
        if self.connected:
            self._disconnect()
        self.root.destroy()
    
    def run(self):
        """啟動監控客戶端"""
        # 自動連接
        self.root.after(1000, self._connect)  # 1秒後自動連接
        
        # 啟動主循環
        self.root.mainloop()

def main():
    """主程式"""
    print("🔍 啟動 MQTT 監控客戶端")
    print("=" * 30)
    
    app = MQTTMonitorClient()
    app.run()

if __name__ == "__main__":
    main()
