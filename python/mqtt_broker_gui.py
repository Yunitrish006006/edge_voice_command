#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
帶GUI的MQTT Broker服務
提供圖形化界面來監控和管理MQTT連接
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import time
import struct
import queue
from datetime import datetime
from config import MQTTConfig

class MQTTBrokerGUI:
    """帶GUI的MQTT Broker"""
    
    def __init__(self):
        # 主視窗
        self.root = tk.Tk()
        self.root.title("🏭 MQTT Broker 控制台")
        
        # 從配置讀取視窗大小
        self.config = MQTTConfig()
        gui_config = self.config.get_gui_config()
        window_width = gui_config['window_width']
        window_height = gui_config['window_height']
        self.root.geometry(f"{window_width}x{window_height}")
        
        # Broker 設定
        self.host = '0.0.0.0'
        self.port = 1883
        self.running = False
        self.server_socket = None
        
        # 數據結構
        self.clients = {}  # client_id -> (socket, address, connect_time)
        self.subscriptions = {}  # topic -> set of client_ids
        self.message_queue = queue.Queue()
        self.stats = {
            'total_connections': 0,
            'active_connections': 0,
            'total_messages': 0,
            'total_subscriptions': 0,
            'uptime_start': None
        }
        
        # 建立UI
        self._setup_ui()
        
        # 啟動訊息處理
        self._start_message_processing()
        
        # 視窗關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_ui(self):
        """建立使用者介面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題區域
        title_frame = ttk.Frame(main_frame)
        title_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(title_frame, text="🏭 MQTT Broker 控制台", 
                               font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        # 狀態指示器
        self.status_label = ttk.Label(title_frame, text="狀態: 停止", 
                                     foreground="red", font=("Arial", 12, "bold"))
        self.status_label.pack(side=tk.RIGHT)
        
        # 控制區域
        control_frame = ttk.LabelFrame(main_frame, text="Broker 控制", padding="10")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 設定框架
        settings_frame = ttk.Frame(control_frame)
        settings_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 主機設定
        ttk.Label(settings_frame, text="監聽地址:").pack(side=tk.LEFT)
        self.host_entry = ttk.Entry(settings_frame, width=15)
        self.host_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.host_entry.insert(0, self.host)
        
        # 端口設定
        ttk.Label(settings_frame, text="端口:").pack(side=tk.LEFT)
        self.port_entry = ttk.Entry(settings_frame, width=8)
        self.port_entry.pack(side=tk.LEFT, padx=(5, 10))
        self.port_entry.insert(0, str(self.port))
        
        # 預設設定按鈕
        presets_frame = ttk.Frame(settings_frame)
        presets_frame.pack(side=tk.LEFT, padx=(20, 0))
        
        preset_configs = [
            ("標準", "0.0.0.0", "1883"),
            ("測試", "127.0.0.1", "1883"),
            ("自訂", "192.168.98.106", "1883")
        ]
        
        for name, host, port in preset_configs:
            btn = ttk.Button(presets_frame, text=name, width=6,
                           command=lambda h=host, p=port: self._set_config(h, p))
            btn.pack(side=tk.LEFT, padx=(0, 3))
        
        # 控制按鈕
        button_frame = ttk.Frame(control_frame)
        button_frame.pack(fill=tk.X)
        
        self.start_btn = ttk.Button(button_frame, text="🚀 啟動 Broker", 
                                   command=self._start_broker)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = ttk.Button(button_frame, text="⏹️ 停止 Broker", 
                                  command=self._stop_broker, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # 重啟按鈕
        restart_btn = ttk.Button(button_frame, text="🔄 重新啟動", 
                                command=self._restart_broker)
        restart_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        # 清除日誌按鈕
        clear_btn = ttk.Button(button_frame, text="🧹 清除日誌", 
                              command=self._clear_logs)
        clear_btn.pack(side=tk.RIGHT)
        
        # 統計資訊區域
        stats_frame = ttk.LabelFrame(main_frame, text="統計資訊", padding="10")
        stats_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 統計資訊顯示
        stats_display_frame = ttk.Frame(stats_frame)
        stats_display_frame.pack(fill=tk.X)
        
        # 左側統計
        left_stats_frame = ttk.Frame(stats_display_frame)
        left_stats_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.connections_label = ttk.Label(left_stats_frame, text="活躍連接: 0")
        self.connections_label.pack(anchor=tk.W)
        
        self.total_connections_label = ttk.Label(left_stats_frame, text="總連接數: 0")
        self.total_connections_label.pack(anchor=tk.W)
        
        # 右側統計
        right_stats_frame = ttk.Frame(stats_display_frame)
        right_stats_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        self.messages_label = ttk.Label(right_stats_frame, text="總訊息數: 0")
        self.messages_label.pack(anchor=tk.E)
        
        self.uptime_label = ttk.Label(right_stats_frame, text="運行時間: 00:00:00")
        self.uptime_label.pack(anchor=tk.E)
        
        # 分頁控制
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 日誌頁面
        log_frame = ttk.Frame(notebook)
        notebook.add(log_frame, text="📝 系統日誌")
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            wrap=tk.WORD, 
            height=15,
            font=("Consolas", 10)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 客戶端頁面
        clients_frame = ttk.Frame(notebook)
        notebook.add(clients_frame, text="👥 連接客戶端")
        
        # 客戶端樹狀圖
        columns = ("ID", "地址", "連接時間", "訂閱數")
        self.clients_tree = ttk.Treeview(clients_frame, columns=columns, show="headings", height=10)
        
        for col in columns:
            self.clients_tree.heading(col, text=col)
            self.clients_tree.column(col, width=150)
        
        # 客戶端樹狀圖滾動條
        clients_scrollbar = ttk.Scrollbar(clients_frame, orient=tk.VERTICAL, 
                                         command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=clients_scrollbar.set)
        
        self.clients_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        clients_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 訂閱主題頁面
        topics_frame = ttk.Frame(notebook)
        notebook.add(topics_frame, text="📡 訂閱主題")
        
        # 主題樹狀圖
        topic_columns = ("主題", "訂閱者數", "訂閱者列表")
        self.topics_tree = ttk.Treeview(topics_frame, columns=topic_columns, show="headings", height=10)
        
        for col in topic_columns:
            self.topics_tree.heading(col, text=col)
            if col == "訂閱者列表":
                self.topics_tree.column(col, width=250)
            else:
                self.topics_tree.column(col, width=150)
        
        # 主題樹狀圖滾動條
        topics_scrollbar = ttk.Scrollbar(topics_frame, orient=tk.VERTICAL, 
                                        command=self.topics_tree.yview)
        self.topics_tree.configure(yscrollcommand=topics_scrollbar.set)
        
        self.topics_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)
        topics_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, pady=5)
        
        # 訊息監控頁面
        messages_frame = ttk.Frame(notebook)
        notebook.add(messages_frame, text="📨 訊息流")
        
        self.messages_text = scrolledtext.ScrolledText(
            messages_frame, 
            wrap=tk.WORD, 
            height=15,
            font=("Consolas", 9)
        )
        self.messages_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 初始化日誌
        self._log("🎛️ MQTT Broker GUI 已初始化")
        self._log(f"💡 準備在 {self.host}:{self.port} 啟動服務")
    
    def _set_config(self, host, port):
        """設定預設配置"""
        self.host_entry.delete(0, tk.END)
        self.host_entry.insert(0, host)
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, port)
    
    def _start_message_processing(self):
        """啟動訊息處理線程"""
        def process_messages():
            while True:
                try:
                    msg_type, data = self.message_queue.get(timeout=0.1)
                    
                    if msg_type == "log":
                        self._update_log(data)
                    elif msg_type == "client_update":
                        self._update_clients_display()
                    elif msg_type == "topic_update":
                        self._update_topics_display()
                    elif msg_type == "message":
                        self._update_messages_display(data)
                    elif msg_type == "stats":
                        self._update_stats_display()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"訊息處理錯誤: {e}")
        
        msg_thread = threading.Thread(target=process_messages, daemon=True)
        msg_thread.start()
        
        # 定期更新運行時間
        self._update_uptime()
    
    def _update_uptime(self):
        """更新運行時間顯示"""
        if self.running and self.stats['uptime_start']:
            uptime_seconds = int(time.time() - self.stats['uptime_start'])
            hours = uptime_seconds // 3600
            minutes = (uptime_seconds % 3600) // 60
            seconds = uptime_seconds % 60
            uptime_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.uptime_label.config(text=f"運行時間: {uptime_str}")
        else:
            self.uptime_label.config(text="運行時間: 00:00:00")
        
        # 每秒更新
        self.root.after(1000, self._update_uptime)
    
    def _log(self, message):
        """添加日誌訊息到隊列"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        self.message_queue.put(("log", log_message))
    
    def _update_log(self, message):
        """更新日誌顯示"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        
        # 限制日誌行數
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            new_content = '\n'.join(lines[-500:])
            self.log_text.delete("1.0", tk.END)
            self.log_text.insert("1.0", new_content)
    
    def _update_clients_display(self):
        """更新客戶端顯示"""
        # 清除現有項目
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        # 添加客戶端資訊
        for client_id, (socket, address, connect_time) in self.clients.items():
            # 計算訂閱數
            subscription_count = sum(1 for topic_subscribers in self.subscriptions.values() 
                                   if client_id in topic_subscribers)
            
            # 格式化連接時間
            connect_time_str = connect_time.strftime("%H:%M:%S")
            
            self.clients_tree.insert("", tk.END, values=(
                client_id, 
                f"{address[0]}:{address[1]}", 
                connect_time_str,
                subscription_count
            ))
    
    def _update_topics_display(self):
        """更新主題顯示"""
        # 清除現有項目
        for item in self.topics_tree.get_children():
            self.topics_tree.delete(item)
        
        # 添加主題資訊
        for topic, subscribers in self.subscriptions.items():
            subscriber_list = ", ".join(sorted(subscribers))
            self.topics_tree.insert("", tk.END, values=(
                topic,
                len(subscribers),
                subscriber_list
            ))
    
    def _update_messages_display(self, message_data):
        """更新訊息流顯示"""
        timestamp, topic, message, client_id = message_data
        display_message = f"[{timestamp}] 📢 {client_id} → {topic}: {message}\n"
        self.messages_text.insert(tk.END, display_message)
        self.messages_text.see(tk.END)
        
        # 限制訊息行數
        lines = self.messages_text.get("1.0", tk.END).split('\n')
        if len(lines) > 500:
            new_content = '\n'.join(lines[-250:])
            self.messages_text.delete("1.0", tk.END)
            self.messages_text.insert("1.0", new_content)
    
    def _update_stats_display(self):
        """更新統計顯示"""
        self.connections_label.config(text=f"活躍連接: {self.stats['active_connections']}")
        self.total_connections_label.config(text=f"總連接數: {self.stats['total_connections']}")
        self.messages_label.config(text=f"總訊息數: {self.stats['total_messages']}")
    
    def _start_broker(self):
        """啟動 Broker"""
        try:
            # 更新配置
            self.host = self.host_entry.get().strip()
            self.port = int(self.port_entry.get().strip())
            
            # 啟動服務器
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            self.stats['uptime_start'] = time.time()
            
            # 更新UI狀態
            self.status_label.config(text="狀態: 運行中", foreground="green")
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL)
            
            # 獲取本機IP
            local_ip = self._get_local_ip()
            
            self._log("🚀 MQTT Broker 已啟動")
            self._log(f"📍 監聽地址: {self.host}:{self.port}")
            self._log(f"🌐 本機IP: {local_ip}:{self.port}")
            
            # 啟動服務器線程
            server_thread = threading.Thread(target=self._run_server, daemon=True)
            server_thread.start()
            
        except Exception as e:
            messagebox.showerror("啟動錯誤", f"Broker 啟動失敗: {e}")
            self._log(f"❌ 啟動失敗: {e}")
    
    def _stop_broker(self):
        """停止 Broker"""
        self.running = False
        
        if self.server_socket:
            self.server_socket.close()
        
        # 關閉所有客戶端連接
        for client_id, (client_socket, _, _) in self.clients.items():
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        self.subscriptions.clear()
        
        # 重置統計
        self.stats['active_connections'] = 0
        self.stats['uptime_start'] = None
        
        # 更新UI狀態
        self.status_label.config(text="狀態: 停止", foreground="red")
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        self._log("⏹️ MQTT Broker 已停止")
        
        # 更新顯示
        self.message_queue.put(("client_update", None))
        self.message_queue.put(("topic_update", None))
        self.message_queue.put(("stats", None))
    
    def _restart_broker(self):
        """重新啟動 Broker"""
        if self.running:
            self._stop_broker()
            time.sleep(1)
        self._start_broker()
    
    def _clear_logs(self):
        """清除日誌"""
        self.log_text.delete("1.0", tk.END)
        self.messages_text.delete("1.0", tk.END)
        self._log("🧹 日誌已清除")
    
    def _get_local_ip(self):
        """獲取本機IP地址"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def _run_server(self):
        """運行服務器主循環"""
        while self.running:
            try:
                client_socket, address = self.server_socket.accept()
                self._log(f"📱 新客戶端連接: {address[0]}:{address[1]}")
                
                # 為每個客戶端創建處理線程
                client_thread = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, address),
                    daemon=True
                )
                client_thread.start()
                
            except socket.error:
                if self.running:
                    self._log("❌ Socket 錯誤")
                break
    
    def _handle_client(self, client_socket, address):
        """處理客戶端連接"""
        client_id = None
        
        try:
            while self.running:
                # 讀取MQTT封包
                data = client_socket.recv(2)
                if not data:
                    break
                
                if len(data) >= 2:
                    msg_type = (data[0] >> 4) & 0x0F
                    remaining_length = data[1]
                    
                    if remaining_length > 0:
                        payload = client_socket.recv(remaining_length)
                        
                        if msg_type == 1:  # CONNECT
                            client_id = self._handle_connect(client_socket, payload, address)
                        elif msg_type == 3:  # PUBLISH
                            self._handle_publish(client_socket, payload, client_id)
                        elif msg_type == 8:  # SUBSCRIBE
                            self._handle_subscribe(client_socket, payload, client_id)
                        elif msg_type == 12:  # PINGREQ
                            self._handle_ping(client_socket, address)
                
        except Exception as e:
            self._log(f"❌ 客戶端 {address[0]}:{address[1]} 錯誤: {e}")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                self.stats['active_connections'] = len(self.clients)
                
                # 清除訂閱
                for topic in list(self.subscriptions.keys()):
                    if client_id in self.subscriptions[topic]:
                        self.subscriptions[topic].remove(client_id)
                        if not self.subscriptions[topic]:
                            del self.subscriptions[topic]
                
                self.message_queue.put(("client_update", None))
                self.message_queue.put(("topic_update", None))
                self.message_queue.put(("stats", None))
            
            try:
                client_socket.close()
            except:
                pass
            self._log(f"🔌 客戶端 {address[0]}:{address[1]} 已斷開")
    
    def _handle_connect(self, client_socket, payload, address):
        """處理 CONNECT 訊息"""
        try:
            # 簡化的 CONNECT 解析
            offset = 10
            
            if len(payload) > offset + 1:
                client_id_len = struct.unpack(">H", payload[offset:offset+2])[0]
                offset += 2
                
                if len(payload) >= offset + client_id_len:
                    client_id = payload[offset:offset+client_id_len].decode('utf-8')
                    
                    # 儲存客戶端
                    self.clients[client_id] = (client_socket, address, datetime.now())
                    self.stats['total_connections'] += 1
                    self.stats['active_connections'] = len(self.clients)
                    
                    # 發送 CONNACK
                    connack = bytes([0x20, 0x02, 0x00, 0x00])
                    client_socket.send(connack)
                    
                    self._log(f"✅ {client_id} ({address[0]}:{address[1]}) 連接成功")
                    
                    self.message_queue.put(("client_update", None))
                    self.message_queue.put(("stats", None))
                    
                    return client_id
        except Exception as e:
            self._log(f"❌ CONNECT 處理錯誤: {e}")
        
        return None
    
    def _handle_publish(self, client_socket, payload, client_id):
        """處理 PUBLISH 訊息"""
        try:
            # 解析主題和訊息
            topic_len = struct.unpack(">H", payload[0:2])[0]
            topic = payload[2:2+topic_len].decode('utf-8')
            message = payload[2+topic_len:].decode('utf-8')
            
            self.stats['total_messages'] += 1
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            self._log(f"📢 {client_id} 發布到 {topic}: {message}")
            
            # 添加到訊息流
            self.message_queue.put(("message", (timestamp, topic, message, client_id)))
            self.message_queue.put(("stats", None))
            
            # 轉發訊息
            self._forward_message(topic, message, client_id)
            
        except Exception as e:
            self._log(f"❌ PUBLISH 處理錯誤: {e}")
    
    def _handle_subscribe(self, client_socket, payload, client_id):
        """處理 SUBSCRIBE 訊息"""
        try:
            # 解析主題
            offset = 2
            topic_len = struct.unpack(">H", payload[offset:offset+2])[0]
            offset += 2
            topic = payload[offset:offset+topic_len].decode('utf-8')
            
            # 添加訂閱
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(client_id)
            
            # 發送 SUBACK
            suback = bytes([0x90, 0x03, payload[0], payload[1], 0x00])
            client_socket.send(suback)
            
            self._log(f"📬 {client_id} 訂閱主題: {topic}")
            
            self.message_queue.put(("client_update", None))
            self.message_queue.put(("topic_update", None))
            
        except Exception as e:
            self._log(f"❌ SUBSCRIBE 處理錯誤: {e}")
    
    def _handle_ping(self, client_socket, address):
        """處理 PING 訊息"""
        try:
            pingresp = bytes([0xD0, 0x00])
            client_socket.send(pingresp)
        except Exception as e:
            self._log(f"❌ PING 處理錯誤: {e}")
    
    def _forward_message(self, topic, message, sender_id):
        """轉發訊息給訂閱者"""
        subscribers = set()
        
        # 查找匹配的訂閱
        for sub_topic in self.subscriptions:
            if self._topic_matches(topic, sub_topic):
                subscribers.update(self.subscriptions[sub_topic])
        
        # 移除發送者
        if sender_id in subscribers:
            subscribers.remove(sender_id)
        
        # 轉發訊息
        forwarded_count = 0
        for subscriber_id in subscribers:
            if subscriber_id in self.clients:
                try:
                    client_socket, _, _ = self.clients[subscriber_id]
                    
                    # 構建 PUBLISH 封包
                    topic_bytes = topic.encode('utf-8')
                    message_bytes = message.encode('utf-8')
                    payload = struct.pack(">H", len(topic_bytes)) + topic_bytes + message_bytes
                    header = bytes([0x30, len(payload)]) + payload
                    
                    client_socket.send(header)
                    forwarded_count += 1
                    
                except Exception as e:
                    self._log(f"❌ 轉發錯誤 {subscriber_id}: {e}")
        
        if forwarded_count > 0:
            self._log(f"📤 已轉發給 {forwarded_count} 個訂閱者")
    
    def _topic_matches(self, published_topic, subscribed_topic):
        """檢查主題是否匹配"""
        if subscribed_topic == published_topic:
            return True
        
        # 支援 + 萬用字元
        if '+' in subscribed_topic:
            sub_parts = subscribed_topic.split('/')
            pub_parts = published_topic.split('/')
            
            if len(sub_parts) == len(pub_parts):
                for sub_part, pub_part in zip(sub_parts, pub_parts):
                    if sub_part != '+' and sub_part != pub_part:
                        return False
                return True
        
        # 支援 # 萬用字元
        if subscribed_topic.endswith('#'):
            prefix = subscribed_topic[:-1]
            return published_topic.startswith(prefix)
        
        return False
    
    def _on_closing(self):
        """視窗關閉處理"""
        if self.running:
            result = messagebox.askyesno("確認", "Broker 正在運行，確定要關閉嗎？")
            if result:
                self._stop_broker()
                self.root.destroy()
        else:
            self.root.destroy()
    
    def run(self):
        """啟動GUI"""
        self.root.mainloop()

def main():
    """主程式"""
    print("🏭 啟動 MQTT Broker GUI")
    app = MQTTBrokerGUI()
    app.run()

if __name__ == "__main__":
    main()
