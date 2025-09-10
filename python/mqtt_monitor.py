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
        
        # 已訂閱主題管理區域
        subscribed_frame = ttk.LabelFrame(main_frame, text="已訂閱主題管理", padding="5")
        subscribed_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 主題列表框架
        topics_list_frame = ttk.Frame(subscribed_frame)
        topics_list_frame.pack(fill=tk.X)
        
        # 主題列表 (使用 Listbox)
        list_frame = ttk.Frame(topics_list_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        ttk.Label(list_frame, text="已訂閱主題:").pack(anchor=tk.W)
        
        # 創建帶滾動條的列表框
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        self.topics_listbox = tk.Listbox(listbox_frame, height=4, 
                                        font=("Consolas", 9))
        scrollbar_topics = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, 
                                        command=self.topics_listbox.yview)
        self.topics_listbox.configure(yscrollcommand=scrollbar_topics.set)
        
        self.topics_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar_topics.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 主題管理按鈕框架
        buttons_frame = ttk.Frame(topics_list_frame)
        buttons_frame.pack(side=tk.RIGHT, padx=(10, 0), fill=tk.Y)
        
        # 取消訂閱按鈕
        unsubscribe_btn = ttk.Button(buttons_frame, text="🗑️ 取消訂閱", 
                                    command=self._unsubscribe_selected)
        unsubscribe_btn.pack(pady=(0, 5), fill=tk.X)
        
        # 清空所有訂閱按鈕
        clear_all_btn = ttk.Button(buttons_frame, text="🧹 清空全部", 
                                  command=self._unsubscribe_all)
        clear_all_btn.pack(pady=(0, 5), fill=tk.X)
        
        # 重新訂閱按鈕
        resubscribe_btn = ttk.Button(buttons_frame, text="🔄 重新訂閱", 
                                    command=self._resubscribe_selected)
        resubscribe_btn.pack(fill=tk.X)
        
        # 訊息顯示區域
        message_frame = ttk.LabelFrame(main_frame, text="MQTT 訊息", padding="5")
        message_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 訊息文字區域
        self.message_text = scrolledtext.ScrolledText(
            message_frame, 
            wrap=tk.WORD, 
            height=15,  # 縮小高度為發送區域讓位
            font=("Consolas", 10)
        )
        self.message_text.pack(fill=tk.BOTH, expand=True)
        
        # 發送訊息區域
        send_frame = ttk.LabelFrame(main_frame, text="發送 MQTT 訊息", padding="5")
        send_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 發送主題輸入
        topic_send_frame = ttk.Frame(send_frame)
        topic_send_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(topic_send_frame, text="發送主題:").pack(side=tk.LEFT)
        self.send_topic_entry = ttk.Entry(topic_send_frame, width=30)
        self.send_topic_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.send_topic_entry.insert(0, "esp32/command")
        
        # 快速主題按鈕
        quick_topics = [("命令", "esp32/command"), ("控制", "esp32/control"), ("測試", "test/message")]
        for name, topic in quick_topics:
            btn = ttk.Button(topic_send_frame, text=name, width=8,
                           command=lambda t=topic: self._set_send_topic(t))
            btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # 發送訊息輸入
        message_send_frame = ttk.Frame(send_frame)
        message_send_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(message_send_frame, text="發送內容:").pack(side=tk.LEFT)
        self.send_message_entry = ttk.Entry(message_send_frame, width=50)
        self.send_message_entry.pack(side=tk.LEFT, padx=(5, 10), fill=tk.X, expand=True)
        self.send_message_entry.bind('<Return>', lambda e: self._send_message())
        
        # 發送按鈕
        send_btn = ttk.Button(message_send_frame, text="📤 發送", 
                             command=self._send_message)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # QoS 選擇
        qos_frame = ttk.Frame(send_frame)
        qos_frame.pack(fill=tk.X)
        
        ttk.Label(qos_frame, text="QoS:").pack(side=tk.LEFT)
        self.qos_var = tk.StringVar(value="0")
        qos_combo = ttk.Combobox(qos_frame, textvariable=self.qos_var, 
                                width=5, values=["0", "1", "2"], state="readonly")
        qos_combo.pack(side=tk.LEFT, padx=(5, 20))
        
        # 保留訊息選項
        self.retain_var = tk.BooleanVar()
        retain_check = ttk.Checkbutton(qos_frame, text="保留訊息 (Retain)", 
                                      variable=self.retain_var)
        retain_check.pack(side=tk.LEFT, padx=(0, 20))
        
        # 預設訊息按鈕
        preset_msg_frame = ttk.Frame(qos_frame)
        preset_msg_frame.pack(side=tk.RIGHT)
        
        preset_messages = [
            ("開燈", "LED_ON"), 
            ("關燈", "LED_OFF"), 
            ("重啟", "RESTART"),
            ("狀態", "GET_STATUS")
        ]
        for name, msg in preset_messages:
            btn = ttk.Button(preset_msg_frame, text=name, width=8,
                           command=lambda m=msg: self._set_send_message(m))
            btn.pack(side=tk.LEFT, padx=(0, 3))
        
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
        """更新已訂閱主題列表"""
        # 清空列表框
        self.topics_listbox.delete(0, tk.END)
        
        # 添加所有主題
        for topic in topics:
            self.topics_listbox.insert(tk.END, topic)
        
        # 更新集合
        self.subscribed_topics = set(topics)
    
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
    
    def _unsubscribe_selected(self):
        """取消訂閱選中的主題"""
        selection = self.topics_listbox.curselection()
        if not selection:
            messagebox.showwarning("選擇錯誤", "請先選擇要取消訂閱的主題")
            return
        
        if not self.connected:
            messagebox.showwarning("連接錯誤", "請先連接到 MQTT Broker")
            return
        
        # 獲取選中的主題
        selected_topic = self.topics_listbox.get(selection[0])
        
        try:
            # 取消訂閱
            self.mqtt_client.unsubscribe(selected_topic)
            
            # 從集合中移除
            if selected_topic in self.subscribed_topics:
                self.subscribed_topics.remove(selected_topic)
            
            # 更新顯示
            self.message_queue.put(("topics", list(self.subscribed_topics)))
            self._add_message(f"🚫 已取消訂閱: {selected_topic}")
            
            if self.debug_mode.get():
                print(f"[DEBUG] 取消訂閱主題: {selected_topic}")
                
        except Exception as e:
            messagebox.showerror("取消訂閱錯誤", f"無法取消訂閱主題: {e}")
    
    def _unsubscribe_all(self):
        """取消所有訂閱"""
        if not self.subscribed_topics:
            messagebox.showinfo("提示", "目前沒有訂閱任何主題")
            return
        
        if not self.connected:
            messagebox.showwarning("連接錯誤", "請先連接到 MQTT Broker")
            return
        
        # 確認對話框
        result = messagebox.askyesno("確認", "確定要取消所有主題的訂閱嗎？")
        if not result:
            return
        
        try:
            # 取消所有訂閱
            for topic in list(self.subscribed_topics):
                self.mqtt_client.unsubscribe(topic)
            
            # 清空集合
            self.subscribed_topics.clear()
            
            # 更新顯示
            self.message_queue.put(("topics", []))
            self._add_message("🧹 已取消所有主題訂閱")
            
            if self.debug_mode.get():
                print("[DEBUG] 已取消所有主題訂閱")
                
        except Exception as e:
            messagebox.showerror("取消訂閱錯誤", f"取消訂閱時發生錯誤: {e}")
    
    def _resubscribe_selected(self):
        """重新訂閱選中的主題"""
        selection = self.topics_listbox.curselection()
        if not selection:
            messagebox.showwarning("選擇錯誤", "請先選擇要重新訂閱的主題")
            return
        
        if not self.connected:
            messagebox.showwarning("連接錯誤", "請先連接到 MQTT Broker")
            return
        
        # 獲取選中的主題
        selected_topic = self.topics_listbox.get(selection[0])
        
        # 重新訂閱
        self._subscribe_to_topic(selected_topic)
    
    def _add_message(self, message):
        """添加系統訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        message_line = f"[{timestamp}] ℹ️ {message}\n"
        self.message_text.insert(tk.END, message_line)
        self.message_text.see(tk.END)
    
    def _set_send_topic(self, topic):
        """設定發送主題"""
        self.send_topic_entry.delete(0, tk.END)
        self.send_topic_entry.insert(0, topic)
        self.send_message_entry.focus()
    
    def _set_send_message(self, message):
        """設定發送訊息"""
        self.send_message_entry.delete(0, tk.END)
        self.send_message_entry.insert(0, message)
    
    def _send_message(self):
        """發送 MQTT 訊息"""
        if not self.connected:
            messagebox.showwarning("連接錯誤", "請先連接到 MQTT Broker")
            return
        
        topic = self.send_topic_entry.get().strip()
        message = self.send_message_entry.get().strip()
        
        if not topic:
            messagebox.showwarning("輸入錯誤", "請輸入發送主題")
            self.send_topic_entry.focus()
            return
        
        if not message:
            messagebox.showwarning("輸入錯誤", "請輸入發送訊息")
            self.send_message_entry.focus()
            return
        
        try:
            qos = int(self.qos_var.get())
            retain = self.retain_var.get()
            
            # 發送訊息
            result = self.mqtt_client.publish(topic, message, qos=qos, retain=retain)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # 顯示發送成功
                timestamp = datetime.now().strftime("%H:%M:%S")
                send_info = f"📤 [QoS:{qos}]"
                if retain:
                    send_info += " [Retain]"
                
                message_line = f"[{timestamp}] {send_info} {topic}: {message}\n"
                self.message_text.insert(tk.END, message_line)
                self.message_text.see(tk.END)
                
                # 清除輸入框
                self.send_message_entry.delete(0, tk.END)
                
                if self.debug_mode.get():
                    print(f"[DEBUG] 訊息發送成功: {topic} -> {message}")
                    
            else:
                messagebox.showerror("發送失敗", f"訊息發送失敗: {result.rc}")
                if self.debug_mode.get():
                    print(f"[DEBUG] 訊息發送失敗: {result.rc}")
                    
        except Exception as e:
            messagebox.showerror("發送錯誤", f"發送訊息時發生錯誤: {e}")
            if self.debug_mode.get():
                print(f"[DEBUG] 發送錯誤: {e}")
    
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
