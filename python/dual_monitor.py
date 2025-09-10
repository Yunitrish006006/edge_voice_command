#!/usr/bin/env python3
"""
雙視窗 MQTT 監控系統
同時顯示 Broker 調適訊息和 MQTT 訊息
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import subprocess
import threading
import queue
import time
import socket
from datetime import datetime
import paho.mqtt.client as mqtt
from config import MQTTConfig

class BrokerLogWindow:
    """Broker 調適訊息視窗"""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("MQTT Broker 調適訊息")
        self.window.geometry("800x600")
        
        # 獲取本機IP地址
        self.local_ip = self._get_local_ip()
        
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(main_frame, text="🏗️ MQTT Broker 調適訊息", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Broker 資訊框架
        info_frame = ttk.LabelFrame(main_frame, text="Broker 資訊", padding="5")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # IP 地址顯示
        ip_label = ttk.Label(info_frame, text=f"📍 Broker IP: {self.local_ip}:1883", 
                            font=("Arial", 10, "bold"), foreground="blue")
        ip_label.pack(side=tk.LEFT)
        
        # 狀態框架
        status_frame = ttk.LabelFrame(main_frame, text="Broker 狀態", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text="狀態: 未啟動", foreground="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.start_btn = ttk.Button(status_frame, text="啟動 Broker", command=self._toggle_broker)
        self.start_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 日誌框架
        log_frame = ttk.LabelFrame(main_frame, text="Broker 日誌", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 日誌文字區域
        self.log_text = scrolledtext.ScrolledText(log_frame, width=100, height=30, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 控制按鈕
        control_frame = ttk.Frame(log_frame)
        control_frame.pack(fill=tk.X, pady=(5, 0))
        
        clear_btn = ttk.Button(control_frame, text="清除日誌", command=self._clear_log)
        clear_btn.pack(side=tk.LEFT)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(control_frame, text="自動捲動", variable=self.auto_scroll_var)
        auto_scroll_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # Broker 程序控制
        self.broker_process = None
        self.log_reader_thread = None
        self.running = False
        
        # 視窗關閉事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _get_local_ip(self):
        """獲取本機IP地址"""
        try:
            # 創建一個臨時socket連接來獲取本機IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                # 連接到一個不可達的地址，不會真正發送數據
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                return local_ip
        except Exception:
            try:
                # 備用方法：獲取hostname對應的IP
                return socket.gethostbyname(socket.gethostname())
            except Exception:
                # 最後的備用選擇
                return "localhost"
        
    def _toggle_broker(self):
        """切換 Broker 啟動/停止"""
        if self.broker_process is None:
            self._start_broker()
        else:
            self._stop_broker()
    
    def _start_broker(self):
        """啟動 Broker"""
        try:
            # 啟動 broker 程序
            self.broker_process = subprocess.Popen(
                ["python", "server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.running = True
            self.status_label.config(text="狀態: 運行中", foreground="green")
            self.start_btn.config(text="停止 Broker")
            
            # 啟動日誌讀取執行緒
            self.log_reader_thread = threading.Thread(target=self._read_broker_logs, daemon=True)
            self.log_reader_thread.start()
            
            self._add_log("✅ Broker 已啟動")
            self._add_log(f"📍 Broker 監聽地址: {self.local_ip}:1883")
            self._add_log(f"🔗 ESP32 可連接至: {self.local_ip}:1883")
            
        except Exception as e:
            self._add_log(f"❌ 啟動 Broker 失敗: {e}")
            messagebox.showerror("錯誤", f"啟動 Broker 失敗: {e}")
    
    def _stop_broker(self):
        """停止 Broker"""
        self.running = False
        
        if self.broker_process:
            try:
                self.broker_process.terminate()
                self.broker_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.broker_process.kill()
            except Exception as e:
                self._add_log(f"⚠️ 停止 Broker 時發生錯誤: {e}")
            
            self.broker_process = None
        
        self.status_label.config(text="狀態: 已停止", foreground="red")
        self.start_btn.config(text="啟動 Broker")
        self._add_log("🛑 Broker 已停止")
    
    def _read_broker_logs(self):
        """讀取 Broker 日誌"""
        try:
            while self.running and self.broker_process:
                if self.broker_process.poll() is not None:
                    # 程序已結束
                    break
                
                line = self.broker_process.stdout.readline()
                if line:
                    # 在主執行緒中更新 GUI
                    self.window.after(0, lambda: self._add_log(line.strip()))
                
        except Exception as e:
            self.window.after(0, lambda: self._add_log(f"❌ 讀取日誌錯誤: {e}"))
        finally:
            if self.running:
                self.window.after(0, self._stop_broker)
    
    def _add_log(self, message):
        """添加日誌訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        
        if self.auto_scroll_var.get():
            self.log_text.see(tk.END)
    
    def _clear_log(self):
        """清除日誌"""
        self.log_text.delete(1.0, tk.END)
    
    def _on_closing(self):
        """視窗關閉事件"""
        if self.broker_process:
            self._stop_broker()
        self.window.destroy()

class MQTTMessageWindow:
    """MQTT 訊息監控視窗"""
    
    def __init__(self):
        self.window = tk.Toplevel()
        self.window.title("MQTT 訊息監控")
        self.window.geometry("800x600")
        
        # 載入配置
        self.config = MQTTConfig()
        
        # MQTT 設定
        broker_host, broker_port = self.config.get_broker_info()
        self.host = broker_host
        self.port = broker_port
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.connected = False
        
        # 訊息佇列
        self.message_queue = queue.Queue()
        
        # 統計
        self.message_count = 0
        
        # 建立 UI
        self._setup_ui()
        self._setup_mqtt()
        
        # 啟動訊息處理
        self.window.after(100, self._process_message_queue)
        
        # 視窗關閉事件
        self.window.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _setup_ui(self):
        """建立使用者介面"""
        # 主框架
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(main_frame, text="📡 MQTT 訊息監控", font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 連接狀態框架
        status_frame = ttk.LabelFrame(main_frame, text="連接狀態", padding="5")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text=f"狀態: 未連接 ({self.host}:{self.port})", foreground="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.connect_btn = ttk.Button(status_frame, text="連接", command=self._toggle_connection)
        self.connect_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 統計框架
        stats_frame = ttk.LabelFrame(main_frame, text="統計資訊", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.message_count_label = ttk.Label(stats_frame, text="收到訊息: 0")
        self.message_count_label.pack(side=tk.LEFT)
        
        # 訂閱主題框架
        topic_frame = ttk.LabelFrame(main_frame, text="訂閱主題管理", padding="5")
        topic_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 目前訂閱的主題顯示
        current_topics_frame = ttk.Frame(topic_frame)
        current_topics_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(current_topics_frame, text="目前訂閱:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        self.subscribed_topics = set()
        self.topic_label = ttk.Label(current_topics_frame, text="未訂閱任何主題", foreground="gray")
        self.topic_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # 動態主題管理框架
        topic_control_frame = ttk.Frame(topic_frame)
        topic_control_frame.pack(fill=tk.X, pady=(5, 0))
        
        # 新主題輸入
        ttk.Label(topic_control_frame, text="新主題:").pack(side=tk.LEFT)
        self.new_topic_var = tk.StringVar()
        self.topic_entry = ttk.Entry(topic_control_frame, textvariable=self.new_topic_var, width=20)
        self.topic_entry.pack(side=tk.LEFT, padx=(5, 5))
        
        # 主題控制按鈕
        self.subscribe_btn = ttk.Button(topic_control_frame, text="訂閱", command=self._subscribe_topic, state="disabled")
        self.subscribe_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.unsubscribe_btn = ttk.Button(topic_control_frame, text="取消訂閱", command=self._unsubscribe_topic, state="disabled")
        self.unsubscribe_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.refresh_btn = ttk.Button(topic_control_frame, text="🔄 刷新", command=self._refresh_topics, state="disabled")
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 預設主題快速按鈕
        preset_frame = ttk.Frame(topic_frame)
        preset_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Label(preset_frame, text="快速訂閱:").pack(side=tk.LEFT)
        
        preset_topics = [
            ("ESP32心跳", "esp32/heartbeat"),
            ("ESP32狀態", "esp32/status"),
            ("ESP32所有", "esp32/+"),
            ("全部主題", "#")
        ]
        
        for name, topic in preset_topics:
            btn = ttk.Button(preset_frame, text=name, 
                           command=lambda t=topic: self._quick_subscribe(t),
                           state="disabled")
            btn.pack(side=tk.LEFT, padx=(5, 0))
            # 儲存按鈕引用以便控制狀態
            if not hasattr(self, 'preset_buttons'):
                self.preset_buttons = []
            self.preset_buttons.append(btn)
        
        # 訊息日誌框架
        log_frame = ttk.LabelFrame(main_frame, text="MQTT 訊息", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 訊息文字區域
        self.message_text = scrolledtext.ScrolledText(log_frame, width=100, height=25, font=("Consolas", 9))
        self.message_text.pack(fill=tk.BOTH, expand=True)
        
        # 控制按鈕
        control_frame = ttk.Frame(log_frame)
        control_frame.pack(fill=tk.X, pady=(5, 0))
        
        clear_btn = ttk.Button(control_frame, text="清除訊息", command=self._clear_messages)
        clear_btn.pack(side=tk.LEFT)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(control_frame, text="自動捲動", variable=self.auto_scroll_var)
        auto_scroll_check.pack(side=tk.LEFT, padx=(10, 0))
        
    def _setup_mqtt(self):
        """設定 MQTT 客戶端"""
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 連接回調"""
        print(f"[DEBUG] MQTT連接回調: rc={rc}")
        if rc == 0:
            self.connected = True
            self.message_queue.put(("status", "connected"))
            # 預設訂閱ESP32主題
            default_topics = ["esp32/+"]
            for topic in default_topics:
                client.subscribe(topic)
                self.subscribed_topics.add(topic)
            
            print(f"[DEBUG] 預設訂閱主題: {default_topics}")
            self.message_queue.put(("topics", list(self.subscribed_topics)))
        else:
            self.message_queue.put(("status", f"error_{rc}"))
            
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息接收回調"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        topic = msg.topic
        try:
            payload = msg.payload.decode('utf-8')
        except UnicodeDecodeError:
            payload = str(msg.payload)
            
        # 調適輸出
        print(f"[DEBUG] 收到MQTT訊息: {topic} -> {payload}")
            
        self.message_queue.put(("message", {
            "timestamp": timestamp,
            "topic": topic,
            "payload": payload
        }))
        
    def _on_disconnect(self, client, userdata, rc):
        """MQTT 斷線回調"""
        self.connected = False
        self.subscribed_topics.clear()
        self.message_queue.put(("status", "disconnected"))
        self.message_queue.put(("topics", []))
        
    def _process_message_queue(self):
        """處理訊息佇列"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self._update_status(data)
                elif msg_type == "message":
                    self._display_message(data)
                elif msg_type == "topics":
                    self._update_subscribed_topics(data)
                    
        except queue.Empty:
            pass
        
        # 繼續檢查佇列
        self.window.after(100, self._process_message_queue)
        
    def _update_status(self, status):
        """更新連接狀態"""
        if status == "connected":
            self.status_label.config(text=f"狀態: 已連接 ({self.host}:{self.port})", foreground="green")
            self.connect_btn.config(text="斷開")
            # 啟用主題管理按鈕
            self._enable_topic_controls(True)
        elif status == "disconnected":
            self.status_label.config(text=f"狀態: 已斷開 ({self.host}:{self.port})", foreground="red")
            self.connect_btn.config(text="連接")
            # 禁用主題管理按鈕
            self._enable_topic_controls(False)
        elif status.startswith("error_"):
            error_code = status.split("_")[1]
            self.status_label.config(text=f"狀態: 連接錯誤 ({error_code})", foreground="red")
            self.connect_btn.config(text="連接")
            # 禁用主題管理按鈕
            self._enable_topic_controls(False)
    
    def _enable_topic_controls(self, enabled):
        """啟用/禁用主題控制按鈕"""
        state = "normal" if enabled else "disabled"
        self.subscribe_btn.config(state=state)
        self.unsubscribe_btn.config(state=state)
        self.refresh_btn.config(state=state)
        
        # 更新預設主題按鈕狀態
        if hasattr(self, 'preset_buttons'):
            for btn in self.preset_buttons:
                btn.config(state=state)
    
    def _update_subscribed_topics(self, topics):
        """更新訂閱主題顯示"""
        if not topics:
            self.topic_label.config(text="未訂閱任何主題", foreground="gray")
        else:
            topic_text = "訂閱: " + ", ".join(topics)
            self.topic_label.config(text=topic_text, foreground="blue")
            
    def _display_message(self, data):
        """顯示收到的訊息"""
        timestamp = data["timestamp"]
        topic = data["topic"]
        payload = data["payload"]
        
        # 調適輸出
        print(f"[DEBUG] 更新GUI顯示: {topic} -> {payload}")
        
        # 更新計數器
        self.message_count += 1
        self.message_count_label.config(text=f"收到訊息: {self.message_count}")
        
        # 在日誌中顯示
        log_text = f"[{timestamp}] 📥 {topic}: {payload}\n"
        self.message_text.insert(tk.END, log_text)
        
        # 自動捲動
        if self.auto_scroll_var.get():
            self.message_text.see(tk.END)
            
    def _clear_messages(self):
        """清除訊息"""
        self.message_text.delete(1.0, tk.END)
        
    def _toggle_connection(self):
        """切換連接狀態"""
        if self.connected:
            self.mqtt_client.disconnect()
        else:
            self._connect_mqtt()
            
    def _connect_mqtt(self):
        """連接 MQTT"""
        try:
            self.mqtt_client.connect(self.host, self.port, 60)
            mqtt_thread = threading.Thread(target=self.mqtt_client.loop_forever, daemon=True)
            mqtt_thread.start()
        except Exception as e:
            self.message_queue.put(("status", f"error_connection: {e}"))
    
    def _subscribe_topic(self):
        """訂閱新主題"""
        topic = self.new_topic_var.get().strip()
        if not topic:
            return
            
        if self.connected and topic not in self.subscribed_topics:
            try:
                self.mqtt_client.subscribe(topic)
                self.subscribed_topics.add(topic)
                self.message_queue.put(("topics", list(self.subscribed_topics)))
                self.new_topic_var.set("")  # 清空輸入框
                print(f"[DEBUG] 手動訂閱主題: {topic}")
            except Exception as e:
                print(f"[ERROR] 訂閱主題失敗: {e}")
    
    def _unsubscribe_topic(self):
        """取消訂閱主題"""
        topic = self.new_topic_var.get().strip()
        if not topic:
            return
            
        if self.connected and topic in self.subscribed_topics:
            try:
                self.mqtt_client.unsubscribe(topic)
                self.subscribed_topics.remove(topic)
                self.message_queue.put(("topics", list(self.subscribed_topics)))
                self.new_topic_var.set("")  # 清空輸入框
                print(f"[DEBUG] 取消訂閱主題: {topic}")
            except Exception as e:
                print(f"[ERROR] 取消訂閱失敗: {e}")
    
    def _quick_subscribe(self, topic):
        """快速訂閱預設主題"""
        if self.connected and topic not in self.subscribed_topics:
            try:
                self.mqtt_client.subscribe(topic)
                self.subscribed_topics.add(topic)
                self.message_queue.put(("topics", list(self.subscribed_topics)))
                print(f"[DEBUG] 快速訂閱主題: {topic}")
            except Exception as e:
                print(f"[ERROR] 快速訂閱失敗: {e}")
    
    def _refresh_topics(self):
        """刷新訂閱主題"""
        if self.connected:
            try:
                # 重新訂閱所有當前主題
                current_topics = list(self.subscribed_topics)
                for topic in current_topics:
                    self.mqtt_client.subscribe(topic)
                self.message_queue.put(("topics", current_topics))
                print(f"[DEBUG] 刷新訂閱主題: {current_topics}")
            except Exception as e:
                print(f"[ERROR] 刷新主題失敗: {e}")
            
    def _on_closing(self):
        """視窗關閉事件"""
        if self.connected:
            self.mqtt_client.disconnect()
        self.window.destroy()

class DualMonitorApp:
    """雙視窗監控主應用程式"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("ESP32 MQTT 雙視窗監控系統")
        self.root.geometry("400x300")
        
        # 子視窗
        self.broker_window = None
        self.mqtt_window = None
        
        self._setup_main_ui()
        
    def _setup_main_ui(self):
        """設定主視窗介面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(main_frame, text="🎛️ ESP32 MQTT 雙視窗監控", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 說明
        desc_label = ttk.Label(main_frame, text="選擇要開啟的監控視窗:", font=("Arial", 12))
        desc_label.pack(pady=(0, 20))
        
        # 按鈕框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)
        
        # Broker 日誌視窗按鈕
        broker_btn = ttk.Button(button_frame, text="🏗️ Broker 調適訊息", 
                               command=self._open_broker_window, width=20)
        broker_btn.pack(pady=5)
        
        # MQTT 訊息視窗按鈕  
        mqtt_btn = ttk.Button(button_frame, text="📡 MQTT 訊息監控", 
                             command=self._open_mqtt_window, width=20)
        mqtt_btn.pack(pady=5)
        
        # 同時開啟按鈕
        both_btn = ttk.Button(button_frame, text="🎛️ 開啟兩個視窗", 
                             command=self._open_both_windows, width=20)
        both_btn.pack(pady=10)
        
        # 狀態標籤
        self.status_label = ttk.Label(main_frame, text="準備就緒", foreground="green")
        self.status_label.pack(pady=(20, 0))
        
    def _open_broker_window(self):
        """開啟 Broker 調適訊息視窗"""
        if self.broker_window is None or not tk.Toplevel.winfo_exists(self.broker_window.window):
            self.broker_window = BrokerLogWindow()
            self.status_label.config(text="Broker 調適視窗已開啟")
        else:
            self.broker_window.window.lift()  # 將視窗提到前面
            
    def _open_mqtt_window(self):
        """開啟 MQTT 訊息監控視窗"""
        if self.mqtt_window is None or not tk.Toplevel.winfo_exists(self.mqtt_window.window):
            self.mqtt_window = MQTTMessageWindow()
            self.status_label.config(text="MQTT 監控視窗已開啟")
        else:
            self.mqtt_window.window.lift()  # 將視窗提到前面
            
    def _open_both_windows(self):
        """同時開啟兩個視窗"""
        self._open_broker_window()
        self._open_mqtt_window()
        self.status_label.config(text="兩個監控視窗已開啟")
        
    def run(self):
        """啟動應用程式"""
        self.root.mainloop()

if __name__ == "__main__":
    print("🎛️ 啟動雙視窗 MQTT 監控系統")
    print("=" * 40)
    
    app = DualMonitorApp()
    app.run()
