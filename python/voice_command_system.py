#!/usr/bin/env python3
"""
MQTT 語音命令系統 - 統一管理類別
整合 broker 服務和 GUI 監控器
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import threading
import time
import json
import queue
from datetime import datetime
import signal
import sys
import paho.mqtt.client as mqtt
from config import MQTTConfig

class MQTTBrokerService:
    """MQTT Broker 服務類別"""
    
    def __init__(self, host='0.0.0.0', port=1883):
        self.host = host
        self.port = port
        self.clients = {}
        self.subscriptions = {}
        self.running = False
        self.server_socket = None
        self.start_time = None
        
    def start(self):
        """啟動 MQTT Broker 服務"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            self.start_time = datetime.now()
            
            print("🏗️  MQTT Broker 服務啟動")
            print("=" * 40)
            print(f"🚀 監聽地址: {self.host}:{self.port}")
            print(f"⏰ 啟動時間: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            
            # 啟動狀態更新執行緒
            status_thread = threading.Thread(target=self._status_monitor, daemon=True)
            status_thread.start()
            
            # 主要連接處理迴圈
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"📱 新客戶端連接: {address}")
                    
                    # 為每個客戶端創建處理執行緒
                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print("❌ Socket 錯誤")
                    break
                    
        except Exception as e:
            print(f"❌ Broker 啟動失敗: {e}")
        finally:
            self.stop()
    
    def stop(self):
        """停止 MQTT Broker 服務"""
        print("🛑 正在停止 Broker 服務...")
        self.running = False
        
        # 關閉所有客戶端連接
        for client_id in list(self.clients.keys()):
            self._disconnect_client(client_id)
        
        # 關閉服務器 socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("🛑 MQTT Broker 已停止")
    
    def _status_monitor(self):
        """狀態監控執行緒"""
        while self.running:
            time.sleep(30)
            if self.running:
                print(f"📊 狀態更新 - 已連接客戶端: {len(self.clients)}")
    
    def _handle_client(self, client_socket, address):
        """處理客戶端連接"""
        client_id = f"{address[0]}:{address[1]}"
        self.clients[client_id] = {
            'socket': client_socket,
            'address': address,
            'subscriptions': set(),
            'connected_at': datetime.now()
        }
        
        try:
            while self.running:
                client_socket.settimeout(1.0)
                
                try:
                    data = client_socket.recv(1024)
                except socket.timeout:
                    continue
                
                if not data:
                    break
                
                # 處理 MQTT 協議
                try:
                    if len(data) >= 2:
                        self._process_mqtt_message(client_id, data)
                except Exception as e:
                    print(f"⚠️  處理訊息錯誤: {e}")
                    
        except Exception as e:
            print(f"❌ 客戶端 {client_id} 錯誤: {e}")
        finally:
            self._disconnect_client(client_id)
    
    def _process_mqtt_message(self, client_id, data):
        """處理 MQTT 協議訊息"""
        if len(data) < 2:
            return
            
        msg_type = (data[0] >> 4) & 0x0F
        
        if msg_type == 1:  # CONNECT
            self._send_connack(client_id)
        elif msg_type == 3:  # PUBLISH
            self._handle_publish(client_id, data)
        elif msg_type == 8:  # SUBSCRIBE
            self._handle_subscribe(client_id, data)
        elif msg_type == 12:  # PINGREQ
            self._send_pingresp(client_id)
    
    def _send_connack(self, client_id):
        """發送連接確認"""
        if client_id in self.clients:
            connack = bytes([0x20, 0x02, 0x00, 0x00])
            try:
                self.clients[client_id]['socket'].send(connack)
                print(f"✅ {client_id} MQTT 連接確認已發送")
            except Exception as e:
                print(f"❌ {client_id} 發送 CONNACK 失敗: {e}")
    
    def _send_pingresp(self, client_id):
        """發送心跳回應"""
        if client_id in self.clients:
            pingresp = bytes([0xD0, 0x00])
            try:
                self.clients[client_id]['socket'].send(pingresp)
                print(f"🏓 {client_id} PING 回應已發送")
            except Exception as e:
                print(f"❌ {client_id} 發送 PINGRESP 失敗: {e}")
    
    def _handle_publish(self, client_id, data):
        """處理發布訊息"""
        try:
            if len(data) > 4:
                topic_length = (data[2] << 8) | data[3]
                if len(data) > 4 + topic_length:
                    topic = data[4:4+topic_length].decode('utf-8')
                    payload = data[4+topic_length:].decode('utf-8', errors='ignore')
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] 📢 發布 - {topic}: {payload}")
                    
                    # 廣播給訂閱的客戶端
                    self._broadcast_to_subscribers(topic, payload, client_id)
        except Exception as e:
            print(f"❌ 處理發布訊息錯誤: {e}")
    
    def _handle_subscribe(self, client_id, data):
        """處理訂閱請求"""
        try:
            print(f"📬 {client_id} 請求訂閱")
            if client_id in self.clients:
                suback = bytes([0x90, 0x03, 0x00, 0x01, 0x00])
                self.clients[client_id]['socket'].send(suback)
        except Exception as e:
            print(f"❌ 處理訂閱錯誤: {e}")
    
    def _broadcast_to_subscribers(self, topic, payload, sender_id):
        """廣播訊息給訂閱者"""
        message = f"TOPIC:{topic}|PAYLOAD:{payload}"
        self._broadcast_message(sender_id, message.encode('utf-8'))
    
    def _broadcast_message(self, sender_id, message):
        """廣播訊息給所有客戶端"""
        disconnected_clients = []
        
        for client_id, client_info in self.clients.items():
            if client_id != sender_id:
                try:
                    client_info['socket'].send(message)
                except:
                    disconnected_clients.append(client_id)
        
        # 清理斷線的客戶端
        for client_id in disconnected_clients:
            self._disconnect_client(client_id)
    
    def _disconnect_client(self, client_id):
        """斷開客戶端連接"""
        if client_id in self.clients:
            try:
                self.clients[client_id]['socket'].close()
            except:
                pass
            
            del self.clients[client_id]
            print(f"🔌 客戶端 {client_id} 已斷開")
    
    def get_status(self):
        """取得服務狀態"""
        return {
            'running': self.running,
            'clients_count': len(self.clients),
            'clients': list(self.clients.keys()),
            'host': self.host,
            'port': self.port,
            'start_time': self.start_time.isoformat() if self.start_time else None
        }

class MQTTMonitorGUI:
    """MQTT 監控器 GUI 類別"""
    
    def __init__(self):
        # 載入配置
        self.config = MQTTConfig()
        
        # 初始化 Tkinter
        self.root = tk.Tk()
        self.root.title("ESP32 語音命令監控系統")
        
        # 視窗配置
        gui_config = self.config.get_gui_config()
        self.root.geometry(f"{gui_config['window_width']}x{gui_config['window_height']}")
        
        # MQTT 設定
        broker_host, broker_port = self.config.get_broker_info()
        self.host = broker_host
        self.port = broker_port
        self.mqtt_client = mqtt.Client(callback_api_version=mqtt.CallbackAPIVersion.VERSION1)
        self.connected = False
        
        # 主題配置
        self.topics = self.config.get_topics()
        
        # 訊息佇列
        self.message_queue = queue.Queue()
        
        # 統計計數器
        self.message_count = 0
        self.voice_command_count = 0
        
        # 建立 UI 和設定 MQTT
        self._setup_ui()
        self._setup_mqtt()
        
        # 啟動訊息處理
        self.root.after(100, self._process_message_queue)
        
    def _setup_ui(self):
        """建立使用者介面"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 標題
        title_label = ttk.Label(main_frame, text="ESP32 語音命令監控系統", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        
        # 連接狀態框架
        status_frame = ttk.LabelFrame(main_frame, text="連接狀態", padding="5")
        status_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.status_label = ttk.Label(status_frame, text=f"狀態: 未連接 ({self.host}:{self.port})", foreground="red")
        self.status_label.grid(row=0, column=0, sticky=tk.W)
        
        self.connect_btn = ttk.Button(status_frame, text="連接", command=self._toggle_connection)
        self.connect_btn.grid(row=0, column=1, padx=(10, 0))
        
        self.broker_mode_btn = ttk.Button(status_frame, text="切換Broker", command=self._switch_broker_mode)
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
        
        self.message_text = scrolledtext.ScrolledText(log_frame, width=80, height=20)
        self.message_text.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 控制按鈕
        control_frame = ttk.Frame(log_frame)
        control_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(5, 0))
        
        clear_btn = ttk.Button(control_frame, text="清除日誌", command=self._clear_log)
        clear_btn.grid(row=0, column=0, sticky=tk.W)
        
        self.auto_scroll_var = tk.BooleanVar(value=True)
        auto_scroll_check = ttk.Checkbutton(control_frame, text="自動捲動", variable=self.auto_scroll_var)
        auto_scroll_check.grid(row=0, column=1, padx=(10, 0))
        
        # 設定 grid 權重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
    def _setup_mqtt(self):
        """設定 MQTT 客戶端"""
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
        
    def _on_connect(self, client, userdata, flags, rc):
        """MQTT 連接回調"""
        if rc == 0:
            self.connected = True
            self.message_queue.put(("status", "connected"))
            # 訂閱主題
            for topic_name, topic_path in self.topics.items():
                client.subscribe(topic_path)
            client.subscribe("esp32/+")
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
            
        self.message_queue.put(("message", {
            "timestamp": timestamp,
            "topic": topic,
            "payload": payload
        }))
        
    def _on_disconnect(self, client, userdata, rc):
        """MQTT 斷線回調"""
        self.connected = False
        self.message_queue.put(("status", "disconnected"))
        
    def _process_message_queue(self):
        """處理訊息佇列"""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "status":
                    self._update_status(data)
                elif msg_type == "message":
                    self._display_message(data)
                    
        except queue.Empty:
            pass
        
        # 繼續檢查佇列
        self.root.after(100, self._process_message_queue)
        
    def _update_status(self, status):
        """更新連接狀態"""
        if status == "connected":
            self.status_label.config(text=f"狀態: 已連接 ({self.host}:{self.port})", foreground="green")
            self.connect_btn.config(text="斷開")
        elif status == "disconnected":
            self.status_label.config(text=f"狀態: 已斷開 ({self.host}:{self.port})", foreground="red")
            self.connect_btn.config(text="連接")
        elif status.startswith("error_"):
            error_code = status.split("_")[1]
            self.status_label.config(text=f"狀態: 連接錯誤 ({error_code})", foreground="red")
            self.connect_btn.config(text="連接")
            
    def _display_message(self, data):
        """顯示收到的訊息"""
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
        
        # 自動捲動
        if self.auto_scroll_var.get():
            self.message_text.see(tk.END)
            
    def _clear_log(self):
        """清除日誌"""
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
            
    def _switch_broker_mode(self):
        """切換 broker 模式"""
        if self.connected:
            messagebox.showwarning("警告", "請先斷開連接再切換 broker")
            return
            
        broker_host, broker_port = self.config.get_broker_info()
        current_mode = "custom" if broker_host == "localhost" else "external"
        new_mode = "external" if current_mode == "custom" else "custom"
        
        self.config.set_broker_mode(new_mode)
        self.host, self.port = self.config.get_broker_info()
        
        mode_names = {"custom": "自建", "external": "外部"}
        self.status_label.config(text=f"狀態: 未連接 ({mode_names[new_mode]}: {self.host}:{self.port})")
        messagebox.showinfo("資訊", f"已切換到 {mode_names[new_mode]} broker\n{self.host}:{self.port}")
        
    def run(self):
        """啟動 GUI"""
        # 自動連接
        self._connect_mqtt()
        
        # 啟動主迴圈
        self.root.mainloop()

class VoiceCommandSystem:
    """語音命令系統主類別"""
    
    def __init__(self):
        self.broker_service = None
        self.monitor_gui = None
        self.broker_thread = None
        
    def start_broker_service(self, host='0.0.0.0', port=1883):
        """啟動 Broker 服務"""
        if self.broker_service and self.broker_service.running:
            print("⚠️  Broker 服務已在運行中")
            return False
        
        self.broker_service = MQTTBrokerService(host, port)
        self.broker_thread = threading.Thread(target=self.broker_service.start, daemon=True)
        self.broker_thread.start()
        
        time.sleep(1)  # 等待服務啟動
        return True
    
    def stop_broker_service(self):
        """停止 Broker 服務"""
        if self.broker_service:
            self.broker_service.stop()
            self.broker_service = None
        
        if self.broker_thread:
            self.broker_thread = None
    
    def start_monitor_gui(self):
        """啟動監控 GUI"""
        self.monitor_gui = MQTTMonitorGUI()
        self.monitor_gui.run()
    
    def get_broker_status(self):
        """取得 Broker 狀態"""
        if self.broker_service:
            return self.broker_service.get_status()
        return {'running': False}

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='ESP32 語音命令 MQTT 系統')
    parser.add_argument('--mode', choices=['broker', 'gui', 'both'], default='both',
                        help='運行模式: broker=只啟動broker, gui=只啟動GUI, both=同時啟動')
    parser.add_argument('--host', default='0.0.0.0', help='Broker 監聽地址')
    parser.add_argument('--port', type=int, default=1883, help='Broker 監聽埠號')
    
    args = parser.parse_args()
    
    # 建立語音命令系統
    system = VoiceCommandSystem()
    
    def signal_handler(signum, frame):
        print("\n🛑 收到停止信號...")
        system.stop_broker_service()
        sys.exit(0)
    
    # 註冊信號處理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        if args.mode in ['broker', 'both']:
            print("🚀 啟動 MQTT Broker 服務...")
            system.start_broker_service(args.host, args.port)
        
        if args.mode in ['gui', 'both']:
            print("🖥️  啟動監控 GUI...")
            system.start_monitor_gui()
        elif args.mode == 'broker':
            # 如果只啟動 broker，保持運行
            try:
                while True:
                    time.sleep(30)
                    status = system.get_broker_status()
                    if status['running']:
                        print(f"📊 Broker 狀態 - 已連接客戶端: {status['clients_count']}")
                    else:
                        break
            except KeyboardInterrupt:
                pass
    
    except KeyboardInterrupt:
        pass
    finally:
        system.stop_broker_service()
