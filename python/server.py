#!/usr/bin/env python3
"""
自建 MQTT Broker 服務器
使用 Python 實現簡單的 MQTT broker
"""

import socket
import threading
import json
import time
from datetime import datetime
import queue
import struct

class SimpleMQTTBroker:
    def __init__(self, host='localhost', port=1883):
        self.host = host
        self.port = port
        self.clients = {}  # 客戶端連接
        self.subscriptions = {}  # 主題訂閱
        self.running = False
        self.server_socket = None
        
    def start(self):
        """啟動 broker"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(10)
            
            self.running = True
            print(f"🚀 MQTT Broker 已啟動")
            print(f"📡 監聽地址: {self.host}:{self.port}")
            print(f"⏰ 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 50)
            
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"📱 新客戶端連接: {address}")
                    
                    # 為每個客戶端創建處理線程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address),
                        daemon=True
                    )
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        print("❌ Socket 錯誤")
                    break
                    
        except Exception as e:
            print(f"❌ 啟動失敗: {e}")
        finally:
            self.stop()
    
    def handle_client(self, client_socket, address):
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
                # 簡化的 MQTT 協議處理
                data = client_socket.recv(1024)
                if not data:
                    break
                
                # 這裡簡化處理，實際 MQTT 協議更複雜
                try:
                    message = data.decode('utf-8', errors='ignore')
                    self.process_message(client_id, message)
                except:
                    # 如果不是文字訊息，嘗試作為二進制處理
                    self.process_binary_message(client_id, data)
                    
        except Exception as e:
            print(f"❌ 客戶端 {client_id} 錯誤: {e}")
        finally:
            self.disconnect_client(client_id)
    
    def process_message(self, client_id, message):
        """處理文字訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] 📨 來自 {client_id}: {message[:100]}...")
        
        # 廣播給所有其他客戶端
        self.broadcast_message(client_id, message)
    
    def process_binary_message(self, client_id, data):
        """處理二進制訊息 (簡化的 MQTT 處理)"""
        if len(data) < 2:
            return
            
        # MQTT 固定標頭
        msg_type = (data[0] >> 4) & 0x0F
        
        if msg_type == 1:  # CONNECT
            self.send_connack(client_id)
        elif msg_type == 3:  # PUBLISH
            self.handle_publish(client_id, data)
        elif msg_type == 8:  # SUBSCRIBE
            self.handle_subscribe(client_id, data)
        elif msg_type == 12:  # PINGREQ
            self.send_pingresp(client_id)
    
    def send_connack(self, client_id):
        """發送連接確認"""
        if client_id in self.clients:
            # CONNACK: 0x20, 0x02, 0x00, 0x00
            connack = bytes([0x20, 0x02, 0x00, 0x00])
            try:
                self.clients[client_id]['socket'].send(connack)
                print(f"✅ {client_id} 連接確認已發送")
            except:
                pass
    
    def send_pingresp(self, client_id):
        """發送心跳回應"""
        if client_id in self.clients:
            # PINGRESP: 0xD0, 0x00
            pingresp = bytes([0xD0, 0x00])
            try:
                self.clients[client_id]['socket'].send(pingresp)
            except:
                pass
    
    def handle_publish(self, client_id, data):
        """處理發布訊息"""
        try:
            # 簡化的主題和載荷提取
            if len(data) > 4:
                topic_length = (data[2] << 8) | data[3]
                if len(data) > 4 + topic_length:
                    topic = data[4:4+topic_length].decode('utf-8')
                    payload = data[4+topic_length:].decode('utf-8', errors='ignore')
                    
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    print(f"[{timestamp}] 📢 發布 - {topic}: {payload}")
                    
                    # 廣播給訂閱的客戶端
                    self.broadcast_to_subscribers(topic, payload, client_id)
        except Exception as e:
            print(f"❌ 處理發布訊息錯誤: {e}")
    
    def handle_subscribe(self, client_id, data):
        """處理訂閱請求"""
        try:
            # 簡化的訂閱處理
            print(f"📬 {client_id} 請求訂閱")
            
            # 發送 SUBACK
            if client_id in self.clients:
                suback = bytes([0x90, 0x03, 0x00, 0x01, 0x00])  # 簡化的 SUBACK
                self.clients[client_id]['socket'].send(suback)
        except Exception as e:
            print(f"❌ 處理訂閱錯誤: {e}")
    
    def broadcast_message(self, sender_id, message):
        """廣播訊息給所有客戶端"""
        disconnected_clients = []
        
        for client_id, client_info in self.clients.items():
            if client_id != sender_id:
                try:
                    client_info['socket'].send(message.encode('utf-8'))
                except:
                    disconnected_clients.append(client_id)
        
        # 清理斷線的客戶端
        for client_id in disconnected_clients:
            self.disconnect_client(client_id)
    
    def broadcast_to_subscribers(self, topic, payload, sender_id):
        """廣播給訂閱者"""
        message = f"TOPIC:{topic}|PAYLOAD:{payload}"
        self.broadcast_message(sender_id, message)
    
    def disconnect_client(self, client_id):
        """斷開客戶端連接"""
        if client_id in self.clients:
            try:
                self.clients[client_id]['socket'].close()
            except:
                pass
            
            del self.clients[client_id]
            print(f"🔌 客戶端 {client_id} 已斷開")
    
    def stop(self):
        """停止 broker"""
        self.running = False
        
        # 關閉所有客戶端連接
        for client_id in list(self.clients.keys()):
            self.disconnect_client(client_id)
        
        # 關閉服務器 socket
        if self.server_socket:
            self.server_socket.close()
        
        print("🛑 MQTT Broker 已停止")
    
    def get_status(self):
        """取得狀態資訊"""
        return {
            'running': self.running,
            'clients_count': len(self.clients),
            'clients': list(self.clients.keys()),
            'host': self.host,
            'port': self.port
        }

class MQTTBrokerManager:
    """MQTT Broker 管理器"""
    
    def __init__(self):
        self.broker = None
        self.broker_thread = None
    
    def start_broker(self, host='0.0.0.0', port=1883):
        """啟動 broker"""
        if self.broker and self.broker.running:
            print("⚠️  Broker 已在運行中")
            return False
        
        self.broker = SimpleMQTTBroker(host, port)
        self.broker_thread = threading.Thread(target=self.broker.start, daemon=True)
        self.broker_thread.start()
        
        # 等待一下確保啟動
        time.sleep(1)
        return True
    
    def stop_broker(self):
        """停止 broker"""
        if self.broker:
            self.broker.stop()
            self.broker = None
        
        if self.broker_thread:
            self.broker_thread = None
    
    def get_status(self):
        """取得狀態"""
        if self.broker:
            return self.broker.get_status()
        return {'running': False}

if __name__ == "__main__":
    import signal
    import sys
    
    def signal_handler(signum, frame):
        print("\n🛑 收到停止信號...")
        manager.stop_broker()
        sys.exit(0)
    
    # 註冊信號處理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("🏗️  自建 MQTT Broker 啟動器")
    print("=" * 40)
    
    manager = MQTTBrokerManager()
    
    # 啟動 broker
    if manager.start_broker(host='0.0.0.0', port=1883):
        print("\n✅ Broker 啟動成功！")
        print("📍 連接資訊:")
        print(f"   - 本地連接: localhost:1883")
        print(f"   - 網路連接: {socket.gethostbyname(socket.gethostname())}:1883")
        print("\n按 Ctrl+C 停止服務")
        
        try:
            # 定期顯示狀態
            while True:
                time.sleep(30)
                status = manager.get_status()
                if status['running']:
                    print(f"📊 狀態更新 - 已連接客戶端: {status['clients_count']}")
                else:
                    break
        except KeyboardInterrupt:
            pass
    else:
        print("❌ Broker 啟動失敗！")
    
    manager.stop_broker()
