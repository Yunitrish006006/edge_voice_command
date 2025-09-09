#!/usr/bin/env python3
"""
MQTT Broker 服務啟動器
使用新的類別結構啟動 MQTT broker
"""

from voice_command_system import VoiceCommandSystem
import signal
import sys
import time

def signal_handler(signum, frame):
    print("\n🛑 收到停止信號...")
    if 'system' in globals():
        system.stop_broker_service()
    sys.exit(0)

if __name__ == "__main__":
    # 註冊信號處理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 建立語音命令系統
    system = VoiceCommandSystem()
    
    # 啟動 Broker 服務
    print("🏗️  自建 MQTT Broker 啟動器")
    print("=" * 40)
    
    if system.start_broker_service(host='0.0.0.0', port=1883):
        print("✅ Broker 啟動成功！")
        print("📍 連接資訊:")
        print("   - 本地連接: localhost:1883")
        
        try:
            import socket
            local_ip = socket.gethostbyname(socket.gethostname())
            print(f"   - 網路連接: {local_ip}:1883")
        except:
            print("   - 網路連接: [無法取得IP]:1883")
        
        print("\n按 Ctrl+C 停止服務")
        
        try:
            # 保持服務運行並定期顯示狀態
            while True:
                time.sleep(30)
                status = system.get_broker_status()
                if status['running']:
                    print(f"📊 狀態更新 - 已連接客戶端: {status['clients_count']}")
                else:
                    break
        except KeyboardInterrupt:
            pass
    else:
        print("❌ Broker 啟動失敗！")
    
    system.stop_broker_service()
