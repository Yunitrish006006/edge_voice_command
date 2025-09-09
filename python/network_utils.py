#!/usr/bin/env python3
"""
IP 位址檢測工具
幫助設定 ESP32 連接到自建 MQTT broker
"""

import socket
import subprocess
import platform

def get_local_ip():
    """取得本機 IP 位址"""
    try:
        # 創建一個 socket 連接到外部地址來取得本機 IP
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        return local_ip
    except Exception:
        return "127.0.0.1"

def get_all_ips():
    """取得所有網路介面的 IP"""
    try:
        hostname = socket.gethostname()
        ip_list = socket.gethostbyname_ex(hostname)[2]
        return [ip for ip in ip_list if not ip.startswith("127.")]
    except Exception:
        return []

def test_port(ip, port):
    """測試端口是否開放"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(2)
            result = s.connect_ex((ip, port))
            return result == 0
    except Exception:
        return False

def generate_esp32_config(ip):
    """生成 ESP32 配置"""
    config = f'''
// ESP32 MQTT 配置 (複製到 main.cpp)
const char *mqtt_server = "{ip}";
const int mqtt_port = 1883;
const char *mqtt_topic = "esp32/voice_command";
const char *client_id = "ESP32_Voice_Command";
'''
    return config

def main():
    print("🔍 網路配置檢測工具")
    print("=" * 40)
    
    # 取得主要 IP
    main_ip = get_local_ip()
    print(f"🌐 主要 IP 位址: {main_ip}")
    
    # 取得所有 IP
    all_ips = get_all_ips()
    if all_ips:
        print(f"📡 所有可用 IP:")
        for i, ip in enumerate(all_ips, 1):
            print(f"   {i}. {ip}")
    
    print("\n🔧 MQTT Broker 狀態檢測:")
    port_1883 = test_port(main_ip, 1883)
    print(f"   端口 1883: {'✅ 開放' if port_1883 else '❌ 關閉'}")
    
    if not port_1883:
        print("\n⚠️  提示: 端口 1883 未開放")
        print("   請先啟動 MQTT Broker:")
        print("   1. 執行 start_custom_mqtt.bat")
        print("   2. 選擇選項 1 或 2 啟動 broker")
    
    print("\n📋 ESP32 配置代碼:")
    print("=" * 40)
    print(generate_esp32_config(main_ip))
    
    print("🔥 設定步驟:")
    print("1. 複製上面的配置代碼到 ESP32 main.cpp")
    print("2. 啟動自建 MQTT Broker")
    print("3. 燒錄並運行 ESP32 程式")
    print("4. 啟動監控程式查看訊息")
    
    print(f"\n🌍 測試連接指令:")
    print(f"mosquitto_pub -h {main_ip} -t esp32/test -m \"Hello\"")
    
    # 保存配置到文件
    try:
        with open("esp32_config.txt", "w", encoding="utf-8") as f:
            f.write(f"ESP32 MQTT 配置\n")
            f.write(f"主機 IP: {main_ip}\n")
            f.write(f"端口: 1883\n")
            f.write(f"配置時間: {socket.gethostname()}\n")
            f.write(generate_esp32_config(main_ip))
        print(f"\n💾 配置已保存到 esp32_config.txt")
    except Exception as e:
        print(f"\n❌ 保存配置失敗: {e}")

if __name__ == "__main__":
    main()
    input("\n按 Enter 鍵退出...")
