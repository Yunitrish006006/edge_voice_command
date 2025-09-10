#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
獨立的 MQTT Broker 服務
專門負責接收和轉發 MQTT 訊息
"""

import socket
import threading
import time
import struct
from datetime import datetime

class SimpleMQTTBroker:
    """簡單的 MQTT Broker 實現"""
    
    def __init__(self, host='0.0.0.0', port=1883):
        self.host = host
        self.port = port
        self.clients = {}  # client_id -> (socket, address)
        self.subscriptions = {}  # topic -> set of client_ids
        self.running = False
        self.server_socket = None
        
    def start(self):
        """啟動 Broker"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            
            # 獲取本機IP
            local_ip = self._get_local_ip()
            
            print("🏗️  MQTT Broker 已啟動")
            print("=" * 40)
            print(f"🚀 監聽地址: {self.host}:{self.port}")
            print(f"📍 本機IP: {local_ip}:{self.port}")
            print(f"⏰ 啟動時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 40)
            
            # 接受連接
            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"📱 新客戶端連接: {address}")
                    
                    # 為每個客戶端創建處理線程
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
        """停止 Broker"""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        
        # 關閉所有客戶端連接
        for client_id, (client_socket, _) in self.clients.items():
            try:
                client_socket.close()
            except:
                pass
        
        self.clients.clear()
        self.subscriptions.clear()
        print("🔌 Broker 已停止")
    
    def _get_local_ip(self):
        """獲取本機IP地址"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except:
            return "127.0.0.1"
    
    def _handle_client(self, client_socket, address):
        """處理客戶端連接"""
        client_id = None
        
        try:
            while self.running:
                # 讀取固定標頭
                data = client_socket.recv(2)
                if not data:
                    break
                
                # 解析 MQTT 封包
                if len(data) >= 2:
                    msg_type = (data[0] >> 4) & 0x0F
                    remaining_length = data[1]
                    
                    # 讀取剩餘數據
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
            print(f"❌ 客戶端 {address} 錯誤: {e}")
        finally:
            if client_id and client_id in self.clients:
                del self.clients[client_id]
                # 清除訂閱
                for topic in list(self.subscriptions.keys()):
                    if client_id in self.subscriptions[topic]:
                        self.subscriptions[topic].remove(client_id)
                        if not self.subscriptions[topic]:
                            del self.subscriptions[topic]
            
            try:
                client_socket.close()
            except:
                pass
            print(f"🔌 客戶端 {address} 已斷開")
    
    def _handle_connect(self, client_socket, payload, address):
        """處理 CONNECT 訊息"""
        try:
            # 簡化的 CONNECT 解析
            # 跳過協議名稱和版本
            offset = 10
            
            # 讀取客戶端ID長度
            if len(payload) > offset + 1:
                client_id_len = struct.unpack(">H", payload[offset:offset+2])[0]
                offset += 2
                
                # 讀取客戶端ID
                if len(payload) >= offset + client_id_len:
                    client_id = payload[offset:offset+client_id_len].decode('utf-8')
                    
                    # 儲存客戶端
                    self.clients[client_id] = (client_socket, address)
                    
                    # 發送 CONNACK
                    connack = bytes([0x20, 0x02, 0x00, 0x00])  # 成功連接
                    client_socket.send(connack)
                    
                    print(f"✅ {address} MQTT 連接確認已發送")
                    return client_id
        except Exception as e:
            print(f"❌ CONNECT 處理錯誤: {e}")
        
        return None
    
    def _handle_publish(self, client_socket, payload, client_id):
        """處理 PUBLISH 訊息"""
        try:
            # 解析主題長度
            topic_len = struct.unpack(">H", payload[0:2])[0]
            topic = payload[2:2+topic_len].decode('utf-8')
            
            # 解析訊息內容
            message = payload[2+topic_len:].decode('utf-8')
            
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] 📢 發布 - {topic}: {message}")
            
            # 轉發給訂閱者
            self._forward_message(topic, message, client_id)
            
        except Exception as e:
            print(f"❌ PUBLISH 處理錯誤: {e}")
    
    def _handle_subscribe(self, client_socket, payload, client_id):
        """處理 SUBSCRIBE 訊息"""
        try:
            # 跳過包ID
            offset = 2
            
            # 解析主題
            topic_len = struct.unpack(">H", payload[offset:offset+2])[0]
            offset += 2
            topic = payload[offset:offset+topic_len].decode('utf-8')
            
            # 添加訂閱
            if topic not in self.subscriptions:
                self.subscriptions[topic] = set()
            self.subscriptions[topic].add(client_id)
            
            # 發送 SUBACK
            suback = bytes([0x90, 0x03, payload[0], payload[1], 0x00])  # QoS 0
            client_socket.send(suback)
            
            print(f"📬 {client_id} 請求訂閱: {topic}")
            
        except Exception as e:
            print(f"❌ SUBSCRIBE 處理錯誤: {e}")
    
    def _handle_ping(self, client_socket, address):
        """處理 PING 訊息"""
        try:
            # 發送 PINGRESP
            pingresp = bytes([0xD0, 0x00])
            client_socket.send(pingresp)
            print(f"🏓 {address} PING 回應已發送")
        except Exception as e:
            print(f"❌ PING 處理錯誤: {e}")
    
    def _forward_message(self, topic, message, sender_id):
        """轉發訊息給訂閱者"""
        # 查找匹配的訂閱
        subscribers = set()
        
        for sub_topic in self.subscriptions:
            if self._topic_matches(topic, sub_topic):
                subscribers.update(self.subscriptions[sub_topic])
        
        # 移除發送者（避免自己收到自己的訊息）
        if sender_id in subscribers:
            subscribers.remove(sender_id)
        
        # 轉發給訂閱者
        for subscriber_id in subscribers:
            if subscriber_id in self.clients:
                try:
                    client_socket, _ = self.clients[subscriber_id]
                    
                    # 構建 PUBLISH 封包
                    topic_bytes = topic.encode('utf-8')
                    message_bytes = message.encode('utf-8')
                    
                    # PUBLISH 封包格式
                    payload = struct.pack(">H", len(topic_bytes)) + topic_bytes + message_bytes
                    header = bytes([0x30, len(payload)]) + payload
                    
                    client_socket.send(header)
                    print(f"📤 轉發給 {subscriber_id}: {topic}")
                    
                except Exception as e:
                    print(f"❌ 轉發錯誤 {subscriber_id}: {e}")
    
    def _topic_matches(self, published_topic, subscribed_topic):
        """檢查主題是否匹配（支援萬用字元）"""
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
        
        return False

def main():
    """主程式"""
    broker = SimpleMQTTBroker()
    
    try:
        print("🎛️ 啟動 MQTT Broker")
        print("按 Ctrl+C 停止服務")
        print()
        
        broker.start()
        
    except KeyboardInterrupt:
        print("\n👋 停止 Broker 服務")
        broker.stop()
    except Exception as e:
        print(f"❌ 服務錯誤: {e}")
        broker.stop()

if __name__ == "__main__":
    main()
