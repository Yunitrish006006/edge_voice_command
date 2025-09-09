#!/usr/bin/env python3
"""
MQTT 語音命令接收器 - GUI 版本 (模組化)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import paho.mqtt.client as mqtt
import json
import threading
from datetime import datetime
import queue
from config import MQTTConfig

class MQTTBrokerGUI:
    def __init__(self):
        # 載入配置
        self.mqtt_config = MQTTConfig()
        
        self.root = tk.Tk()
        self.root.title("ESP32 語音命令監控器")
        
        # 從配置取得視窗大小
        gui_config = self.mqtt_config.get_gui_config()
        self.root.geometry(f"{gui_config['window_width']}x{gui_config['window_height']}")
        
        # MQTT 設定
        broker_host, broker_port = self.mqtt_config.get_broker_info()
        self.host = broker_host
        self.port = broker_port
        self.client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.connected = False
        
        # 主題配置
        self.topics = self.mqtt_config.get_topics()
        
        # 訊息佇列用於線程間通信
        self.message_queue = queue.Queue()
        
        # 建立 UI
        self.setup_ui()
        self.setup_mqtt()
        
        # 定期檢查訊息佇列
        self.root.after(100, self.process_queue)
        
    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 標題
        title_label = ttk.Label(main_frame, text="ESP32 語音命令監控器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 連接狀態框架
        status_frame = ttk.LabelFrame(main_frame, text="連接狀態", padding="5")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text=f"狀態: 未連接 ({self.host}:{self.port})", foreground="red")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.connect_btn = ttk.Button(status_frame, text="連接", command=self.toggle_connection)
        self.connect_btn.grid(row=0, column=1, padx=(10, 0))
        
        # Broker 模式切換
        self.broker_mode_btn = ttk.Button(status_frame, text="切換Broker", command=self.switch_broker_mode)
        self.broker_mode_btn.grid(row=0, column=2, padx=(10, 0))
        
        # 統計資訊框架
        stats_frame = ttk.LabelFrame(main_frame, text="統計資訊", padding="5")
        stats_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.message_count_label = ttk.Label(stats_frame, text="收到訊息: 0")
        self.message_count_label.grid(row=0, column=0, sticky=tk.W)
        
        self.voice_command_label = ttk.Label(stats_frame, text="語音命令: 0")
        self.voice_command_label.grid(row=0, column=1, padx=(20, 0), sticky=tk.W)
        
        # 最新語音命令框架
        latest_frame = ttk.LabelFrame(main_frame, text="最新語音命令", padding="5")
        latest_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.latest_command_label = ttk.Label(latest_frame, text="無", font=("Arial", 12), foreground="blue")
        self.latest_command_label.grid(row=0, column=0, sticky=tk.W)
        
        # 訊息日誌框架
        log_frame = ttk.LabelFrame(main_frame, text="訊息日誌", padding="5")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # 訊息顯示區域
        self.message_text = scrolledtext.ScrolledText(log_frame, width=80, height=20)
        self.message_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 清除按鈕
        clear_btn = ttk.Button(log_frame, text="清除日誌", command=self.clear_log)
        clear_btn.grid(row=1, column=0, pady=(5, 0), sticky=tk.W)
        
        # 自動捲動開關
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(log_frame, text="自動捲動", variable=self.auto_scroll_var)
        auto_scroll_check.grid(row=1, column=1, pady=(5, 0), sticky=tk.E)
        
        # 設定權重讓界面可以調整大小
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # 計數器
        self.message_count = 0
        self.voice_command_count = 0
        
    def setup_mqtt(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            self.message_queue.put(("status", "connected"))
            # 訂閱配置的主題
            for topic_name, topic_path in self.topics.items():
                client.subscribe(topic_path)
            client.subscribe("esp32/+")  # 訂閱所有 esp32 主題
        else:
            self.message_queue.put(("status", f"error_{rc}"))
            
    def on_message(self, client, userdata, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        topic = msg.topic
        try:
            payload = msg.payload.decode('utf-8')
        except UnicodeDecodeError:
            payload = str(msg.payload)
            
        self.message_queue.put(("message", {
            "timestamp": timestamp,
            "topic": topic,
            "payload": payload
        }))
        
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        self.message_queue.put(("status", "disconnected"))
        
    def switch_broker_mode(self):
        """切換 broker 模式"""
        if self.connected:
            messagebox.showwarning("警告", "請先斷開連接再切換 broker")
            return
            
        # 取得當前模式
        broker_host, broker_port = self.mqtt_config.get_broker_info()
        
        current_mode = "custom" if broker_host == "localhost" else "external"
        new_mode = "external" if current_mode == "custom" else "custom"
        
        # 更新配置
        self.mqtt_config.set_broker_mode(new_mode)
        
        # 重新載入配置
        self.host, self.port = self.mqtt_config.get_broker_info()
        
        # 更新狀態顯示
        mode_names = {
            "custom": "自建",
            "external": "外部"
        }
        self.status_label.config(text=f"狀態: 未連接 ({mode_names[new_mode]}: {self.host}:{self.port})")
        
        messagebox.showinfo("資訊", f"已切換到 {mode_names[new_mode]} broker\n{self.host}:{self.port}")
        
    def process_queue(self):
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self.update_status(data)
                elif msg_type == "message":
                    self.display_message(data)
                    
        except queue.Empty:
            pass
        
        # 繼續檢查佇列
        self.root.after(100, self.process_queue)
        
    def update_status(self, status):
        if status == "connected":
            self.status_label.config(text=f"狀態: 已連接 ({self.host}:{self.port})", foreground="green")
            self.connect_btn.config(text="斷開")
        elif status == "disconnected":
            self.status_label.config(text=f"狀態: 已斷開 ({self.host}:{self.port})", foreground="red")
            self.connect_btn.config(text="連接")
        elif status.startswith("error_"):
            error_code = status.split("_")[1]
            self.status_label.config(text=f"狀態: 連接錯誤 ({error_code}) - {self.host}:{self.port}", foreground="red")
            self.connect_btn.config(text="連接")
            
    def display_message(self, data):
        timestamp = data["timestamp"]
        topic = data["topic"]
        payload = data["payload"]
        
        # 更新計數器
        self.message_count += 1
        self.message_count_label.config(text=f"收到訊息: {self.message_count}")
        
        # 檢查是否為語音命令
        if topic == self.topics['voice_command']:
            self.voice_command_count += 1
            self.voice_command_label.config(text=f"語音命令: {self.voice_command_count}")
            self.latest_command_label.config(text=payload)
        
        # 在日誌中顯示
        log_text = f"[{timestamp}] {topic}: {payload}\n"
        self.message_text.insert(tk.END, log_text)
        
        # 自動捲動到底部
        if self.auto_scroll_var.get():
            self.message_text.see(tk.END)
            
    def clear_log(self):
        self.message_text.delete(1.0, tk.END)
        
    def toggle_connection(self):
        if self.connected:
            self.client.disconnect()
        else:
            self.connect_mqtt()
            
    def connect_mqtt(self):
        try:
            self.client.connect(self.host, self.port, 60)
            # 在背景執行緒中運行 MQTT loop
            mqtt_thread = threading.Thread(target=self.client.loop_forever, daemon=True)
            mqtt_thread.start()
        except Exception as e:
            self.message_queue.put(("status", f"error_connection: {e}"))
            
    def run(self):
        # 自動連接
        self.connect_mqtt()
        
        # 啟動 GUI
        self.root.mainloop()

if __name__ == "__main__":
    app = MQTTBrokerGUI()
    app.run()
