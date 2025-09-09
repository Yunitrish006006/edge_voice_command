#!/usr/bin/env python3
"""
MQTT 語音命令監控器 - GUI 版本
使用新的類別結構啟動監控介面
"""

from voice_command_system import VoiceCommandSystem

if __name__ == "__main__":
    print("🖥️  啟動 MQTT 語音命令監控器")
    print("=" * 40)
    
    # 建立語音命令系統
    system = VoiceCommandSystem()
    
    try:
        # 啟動監控 GUI
        system.start_monitor_gui()
    except KeyboardInterrupt:
        print("\n👋 使用者中斷，正在退出...")
    except Exception as e:
        print(f"❌ GUI 啟動失敗: {e}")
    
    print("👋 監控器已關閉")
