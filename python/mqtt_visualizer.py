#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ESP32 音訊數據 MQTT 視覺化監控器
基於原始 mqtt_monitor.py，增加即時圖表顯示功能
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import paho.mqtt.client as mqtt
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
import threading
import queue
import time
import json
from datetime import datetime
from collections import deque
from config import MQTTConfig

class ESP32AudioVisualizer:
    """ESP32 音訊數據視覺化監控器"""
    
    def __init__(self):
        # 主視窗
        self.root = tk.Tk()
        self.root.title("🎵 ESP32 音訊數據視覺化監控器")
        
        # MQTT 設定
        self.config = MQTTConfig()
        
        # 從配置檔讀取視窗大小
        gui_config = self.config.get_gui_config()
        window_width = gui_config['window_width']
        window_height = gui_config['window_height']
        self.root.geometry(f"{window_width}x{window_height}")
        
        self.broker_host, self.broker_port = self.config.get_broker_info()
        self.mqtt_client = None
        self.connected = False
        
        # 數據儲存
        self.volume_data = deque(maxlen=100)  # 音量數據
        self.frequency_data = deque(maxlen=50)  # 頻率數據
        self.timestamps = deque(maxlen=100)  # 時間戳
        self.message_queue = queue.Queue()
        self.message_count = 0
        
        # 統計數據
        self.stats = {
            'total_messages': 0,
            'volume_max': 0.0,
            'volume_avg': 0.0,
            'voice_detections': 0,
            'last_detection': None
        }
        
        # 創建 UI
        self._setup_ui()
        self._setup_mqtt()
        self._setup_plots()
        
        # 啟動數據處理
        self._start_message_processing()
        self._start_plot_animation()
        
        # 視窗關閉事件
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_ui(self):
        """建立使用者介面"""
        # 建立主要框架
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(main_frame, text="🎵 ESP32 音訊數據視覺化監控器", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 建立左右分割區域
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左側控制面板
        control_frame = ttk.Frame(content_frame, width=350)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        control_frame.pack_propagate(False)
        
        # 右側圖表區域
        plot_frame = ttk.Frame(content_frame)
        plot_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # 設定控制面板
        self._setup_control_panel(control_frame)
        
        # 設定圖表區域
        self._setup_plot_area(plot_frame)
    
    def _setup_control_panel(self, parent):
        """設定控制面板"""
        # MQTT 連接設定
        connection_frame = ttk.LabelFrame(parent, text="MQTT 連接", padding="5")
        connection_frame.pack(fill=tk.X, pady=(0, 5))
        
        # Broker 設定
        broker_frame = ttk.Frame(connection_frame)
        broker_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(broker_frame, text="Broker:").pack(side=tk.LEFT)
        self.broker_entry = ttk.Entry(broker_frame, width=15)
        self.broker_entry.pack(side=tk.LEFT, padx=(5, 5))
        self.broker_entry.insert(0, self.broker_host)
        
        # 連接按鈕
        self.connect_btn = ttk.Button(broker_frame, text="連接", 
                                     command=self._toggle_connection)
        self.connect_btn.pack(side=tk.RIGHT)
        
        # 狀態顯示
        self.status_label = ttk.Label(connection_frame, text="狀態: 未連接", 
                                     foreground="red")
        self.status_label.pack()
        
        # 主題訂閱
        topic_frame = ttk.LabelFrame(parent, text="主題訂閱", padding="5")
        topic_frame.pack(fill=tk.X, pady=(0, 5))
        
        # ESP32 音訊主題按鈕
        audio_topics = [
            ("音量數據", "esp32/audio/volume"),
            ("頻率數據", "esp32/audio/frequencies"),
            ("語音檢測", "esp32/voice/detected"),
            ("所有音訊", "esp32/audio/+"),
            ("ESP32全部", "esp32/+")
        ]
        
        for i, (name, topic) in enumerate(audio_topics):
            btn = ttk.Button(topic_frame, text=name, width=12,
                           command=lambda t=topic: self._subscribe_topic(t))
            btn.pack(fill=tk.X, pady=1)
        
        # 數據統計
        stats_frame = ttk.LabelFrame(parent, text="數據統計", padding="5")
        stats_frame.pack(fill=tk.X, pady=(0, 5))
        
        self.stats_text = tk.Text(stats_frame, height=8, width=35, 
                                 font=("Consolas", 9))
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # 控制按鈕
        control_frame = ttk.LabelFrame(parent, text="控制", padding="5")
        control_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Button(control_frame, text="🔄 重置數據", 
                  command=self._reset_data).pack(fill=tk.X, pady=1)
        ttk.Button(control_frame, text="💾 儲存數據", 
                  command=self._save_data).pack(fill=tk.X, pady=1)
        ttk.Button(control_frame, text="📊 重新繪圖", 
                  command=self._refresh_plots).pack(fill=tk.X, pady=1)
        
        # 發送測試指令
        test_frame = ttk.LabelFrame(parent, text="ESP32 控制", padding="5")
        test_frame.pack(fill=tk.X, pady=(0, 5))
        
        test_commands = [
            ("🎙️ 開始錄音", "start_audio"),
            ("⏹️ 停止錄音", "stop_audio"),
            ("📊 音訊狀態", "audio_status"),
            ("🔊 播放提示音", "play_beep"),
            ("📡 系統狀態", "status")
        ]
        
        for name, cmd in test_commands:
            btn = ttk.Button(test_frame, text=name, width=12,
                           command=lambda c=cmd: self._send_command(c))
            btn.pack(fill=tk.X, pady=1)
        
        # 訊息記錄
        log_frame = ttk.LabelFrame(parent, text="訊息記錄", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, 
                                                 font=("Consolas", 8))
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def _setup_plot_area(self, parent):
        """設定圖表區域"""
        # 建立 matplotlib 圖表
        self.fig, ((self.ax1, self.ax2), (self.ax3, self.ax4)) = plt.subplots(
            2, 2, figsize=(12, 8)
        )
        self.fig.suptitle('ESP32 音訊數據即時監控', fontsize=14, fontweight='bold')
        
        # 嵌入到 tkinter
        self.canvas = FigureCanvasTkAgg(self.fig, parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def _setup_plots(self):
        """設定各個圖表"""
        # 1. 即時音量圖
        self.ax1.set_title('即時音量 (RMS)', fontweight='bold')
        self.ax1.set_ylabel('音量')
        self.ax1.set_xlabel('時間 (樣本)')
        self.ax1.grid(True, alpha=0.3)
        self.volume_line, = self.ax1.plot([], [], 'b-', linewidth=2, label='音量')
        self.threshold_line = self.ax1.axhline(y=0.1, color='r', linestyle='--', 
                                              label='閾值', alpha=0.7)
        self.ax1.legend()
        
        # 2. 頻率分析圖
        self.ax2.set_title('頻率分析', fontweight='bold')
        self.ax2.set_ylabel('振幅')
        self.ax2.set_xlabel('頻率段')
        self.ax2.grid(True, alpha=0.3)
        # 初始化頻率柱狀圖
        self.freq_bars = self.ax2.bar(range(10), [0]*10, alpha=0.7, color='green')
        
        # 3. 音量統計直方圖
        self.ax3.set_title('音量分佈直方圖', fontweight='bold')
        self.ax3.set_ylabel('次數')
        self.ax3.set_xlabel('音量範圍')
        self.ax3.grid(True, alpha=0.3)
        
        # 4. 語音活動時間線
        self.ax4.set_title('語音活動檢測', fontweight='bold')
        self.ax4.set_ylabel('檢測狀態')
        self.ax4.set_xlabel('時間')
        self.ax4.grid(True, alpha=0.3)
        self.ax4.set_ylim(-0.5, 1.5)
        self.voice_timeline, = self.ax4.plot([], [], 'ro-', markersize=4, 
                                            label='語音檢測')
        self.ax4.legend()
        
        # 調整佈局
        self.fig.tight_layout()
    
    def _setup_mqtt(self):
        """設定 MQTT 客戶端"""
        client_id = f"Visualizer_{int(time.time())}"
        self.mqtt_client = mqtt.Client(
            client_id=client_id,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2
        )
        
        # 設定回調
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect
    
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """MQTT 連接回調"""
        if reason_code == 0:
            self.connected = True
            self.message_queue.put(("status", "connected"))
            # 自動訂閱音訊主題
            client.subscribe("esp32/audio/+")
            client.subscribe("esp32/voice/+")
            self._log_message("✅ 已連接並訂閱音訊主題")
        else:
            self.message_queue.put(("status", f"error_{reason_code}"))
    
    def _on_message(self, client, userdata, msg):
        """MQTT 訊息接收回調"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8', errors='ignore')
        timestamp = time.time()
        
        # 處理不同類型的訊息
        if topic == "esp32/audio/volume":
            self._process_volume_data(payload, timestamp)
        elif topic == "esp32/audio/frequencies":
            self._process_frequency_data(payload, timestamp)
        elif topic == "esp32/voice/detected":
            self._process_voice_detection(payload, timestamp)
        
        # 加入訊息佇列
        self.message_queue.put(("message", {
            "topic": topic,
            "payload": payload,
            "timestamp": timestamp
        }))
    
    def _on_disconnect(self, client, userdata, flags, reason_code, properties):
        """MQTT 斷線回調"""
        self.connected = False
        self.message_queue.put(("status", "disconnected"))
    
    def _process_volume_data(self, payload, timestamp):
        """處理音量數據"""
        try:
            volume = float(payload)
            self.volume_data.append(volume)
            self.timestamps.append(timestamp)
            
            # 更新統計
            self.stats['volume_max'] = max(self.stats['volume_max'], volume)
            if len(self.volume_data) > 0:
                self.stats['volume_avg'] = np.mean(list(self.volume_data))
            
        except ValueError:
            self._log_message(f"⚠️ 無效音量數據: {payload}")
    
    def _process_frequency_data(self, payload, timestamp):
        """處理頻率數據"""
        try:
            # 嘗試解析為數字列表
            if ',' in payload:
                frequencies = [float(f.strip()) for f in payload.split(',')]
            else:
                # 如果是 JSON 格式
                frequencies = json.loads(payload)
            
            self.frequency_data.append(frequencies[:10])  # 只保留前10個
            
        except (ValueError, json.JSONDecodeError):
            self._log_message(f"⚠️ 無效頻率數據: {payload}")
    
    def _process_voice_detection(self, payload, timestamp):
        """處理語音檢測"""
        if payload.lower() in ['true', '1', 'detected']:
            self.stats['voice_detections'] += 1
            self.stats['last_detection'] = datetime.fromtimestamp(timestamp)
            self._log_message("🗣️ 檢測到語音活動！")
    
    def _start_message_processing(self):
        """啟動訊息處理線程"""
        def process_messages():
            while True:
                try:
                    msg_type, data = self.message_queue.get(timeout=0.1)
                    
                    if msg_type == "status":
                        self._update_status(data)
                    elif msg_type == "message":
                        self._update_stats()
                        self._log_mqtt_message(data)
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    print(f"訊息處理錯誤: {e}")
        
        msg_thread = threading.Thread(target=process_messages, daemon=True)
        msg_thread.start()
    
    def _start_plot_animation(self):
        """啟動圖表動畫"""
        def update_plots(frame):
            self._update_volume_plot()
            self._update_frequency_plot()
            self._update_histogram()
            self._update_voice_timeline()
            return []
        
        # 每500ms更新一次圖表
        self.ani = animation.FuncAnimation(
            self.fig, update_plots, interval=500, blit=False
        )
    
    def _update_volume_plot(self):
        """更新音量圖表"""
        if len(self.volume_data) > 1:
            x_data = list(range(len(self.volume_data)))
            y_data = list(self.volume_data)
            
            self.volume_line.set_data(x_data, y_data)
            self.ax1.relim()
            self.ax1.autoscale_view()
            
            # 動態調整閾值線
            if len(y_data) > 0:
                max_vol = max(y_data)
                self.ax1.set_ylim(0, max(0.5, max_vol * 1.1))
    
    def _update_frequency_plot(self):
        """更新頻率圖表"""
        if self.frequency_data:
            latest_freq = list(self.frequency_data)[-1]
            
            # 確保有足夠的數據
            while len(latest_freq) < 10:
                latest_freq.append(0)
            
            # 更新柱狀圖
            for i, bar in enumerate(self.freq_bars):
                if i < len(latest_freq):
                    bar.set_height(latest_freq[i])
            
            # 調整Y軸範圍
            if latest_freq:
                max_freq = max(latest_freq)
                self.ax2.set_ylim(0, max(100, max_freq * 1.1))
    
    def _update_histogram(self):
        """更新音量分佈直方圖"""
        if len(self.volume_data) > 10:
            self.ax3.clear()
            self.ax3.hist(list(self.volume_data), bins=20, alpha=0.7, 
                         color='blue', edgecolor='black')
            self.ax3.set_title('音量分佈直方圖', fontweight='bold')
            self.ax3.set_ylabel('次數')
            self.ax3.set_xlabel('音量範圍')
            self.ax3.grid(True, alpha=0.3)
    
    def _update_voice_timeline(self):
        """更新語音檢測時間線"""
        # 這裡可以添加語音檢測的時間線顯示
        # 暫時顯示檢測次數的變化
        if self.stats['voice_detections'] > 0:
            detection_times = [i for i in range(self.stats['voice_detections'])]
            detection_values = [1] * self.stats['voice_detections']
            
            self.voice_timeline.set_data(detection_times, detection_values)
            if detection_times:
                self.ax4.set_xlim(0, max(10, max(detection_times) + 1))
    
    def _update_status(self, status):
        """更新連接狀態"""
        if status == "connected":
            self.status_label.config(text="狀態: 已連接", foreground="green")
            self.connect_btn.config(text="斷開")
        elif status == "disconnected":
            self.status_label.config(text="狀態: 已斷開", foreground="red")
            self.connect_btn.config(text="連接")
        else:
            self.status_label.config(text=f"狀態: 錯誤", foreground="orange")
            self.connect_btn.config(text="連接")
    
    def _update_stats(self):
        """更新統計顯示"""
        self.stats['total_messages'] += 1
        
        stats_text = f"""📊 數據統計
━━━━━━━━━━━━━━━━━━━━
📨 總訊息數: {self.stats['total_messages']}
🔊 音量數據: {len(self.volume_data)} 樣本
🎵 頻率數據: {len(self.frequency_data)} 組
🗣️ 語音檢測: {self.stats['voice_detections']} 次

📈 音量統計:
  最大音量: {self.stats['volume_max']:.3f}
  平均音量: {self.stats['volume_avg']:.3f}
  當前樣本: {len(self.volume_data)}/100

🕐 最後檢測: 
  {self.stats['last_detection'] or '尚未檢測'}
"""
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)
    
    def _log_message(self, message):
        """記錄系統訊息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_line = f"[{timestamp}] {message}\n"
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)
    
    def _log_mqtt_message(self, msg_data):
        """記錄 MQTT 訊息"""
        timestamp = datetime.fromtimestamp(msg_data['timestamp']).strftime("%H:%M:%S")
        topic = msg_data['topic']
        payload = msg_data['payload']
        
        # 簡化顯示
        short_payload = payload[:50] + "..." if len(payload) > 50 else payload
        log_line = f"[{timestamp}] 📡 {topic}: {short_payload}\n"
        
        self.log_text.insert(tk.END, log_line)
        self.log_text.see(tk.END)
        
        # 限制日誌長度
        lines = self.log_text.get(1.0, tk.END).split('\n')
        if len(lines) > 100:
            new_content = '\n'.join(lines[-50:])
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(1.0, new_content)
    
    def _toggle_connection(self):
        """切換連接狀態"""
        if self.connected:
            self._disconnect()
        else:
            self._connect()
    
    def _connect(self):
        """連接到 MQTT Broker"""
        try:
            broker = self.broker_entry.get().strip() or self.broker_host
            self.mqtt_client.connect(broker, self.broker_port, 60)
            self.mqtt_client.loop_start()
            self._log_message(f"🔗 正在連接到 {broker}...")
            
        except Exception as e:
            messagebox.showerror("連接錯誤", f"無法連接: {e}")
    
    def _disconnect(self):
        """斷開連接"""
        try:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            self._log_message("🔌 已斷開連接")
        except Exception as e:
            print(f"斷開錯誤: {e}")
    
    def _subscribe_topic(self, topic):
        """訂閱主題"""
        if self.connected:
            self.mqtt_client.subscribe(topic)
            self._log_message(f"📡 已訂閱: {topic}")
        else:
            messagebox.showwarning("連接錯誤", "請先連接到 MQTT Broker")
    
    def _send_command(self, command):
        """發送控制指令"""
        if self.connected:
            self.mqtt_client.publish("esp32/command", command)
            self._log_message(f"📤 發送指令: {command}")
        else:
            messagebox.showwarning("連接錯誤", "請先連接到 MQTT Broker")
    
    def _reset_data(self):
        """重置所有數據"""
        self.volume_data.clear()
        self.frequency_data.clear()
        self.timestamps.clear()
        
        self.stats = {
            'total_messages': 0,
            'volume_max': 0.0,
            'volume_avg': 0.0,
            'voice_detections': 0,
            'last_detection': None
        }
        
        self._log_message("🔄 數據已重置")
        self._refresh_plots()
    
    def _save_data(self):
        """儲存數據到檔案"""
        try:
            data = {
                'volume_data': list(self.volume_data),
                'frequency_data': [list(freq) for freq in self.frequency_data],
                'timestamps': list(self.timestamps),
                'stats': self.stats.copy()
            }
            
            filename = f"esp32_audio_data_{int(time.time())}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            self._log_message(f"💾 數據已儲存到 {filename}")
            messagebox.showinfo("儲存成功", f"數據已儲存到 {filename}")
            
        except Exception as e:
            messagebox.showerror("儲存失敗", f"無法儲存數據: {e}")
    
    def _refresh_plots(self):
        """重新繪製圖表"""
        self.canvas.draw()
        self._log_message("📊 圖表已重新繪製")
    
    def _on_closing(self):
        """視窗關閉處理"""
        if self.connected:
            self._disconnect()
        self.root.destroy()
    
    def run(self):
        """啟動應用程式"""
        # 自動連接
        self.root.after(1000, self._connect)
        
        # 啟動主循環
        self.root.mainloop()

def main():
    """主程式"""
    print("🎵 啟動 ESP32 音訊數據視覺化監控器")
    print("=" * 40)
    
    # 檢查必要的套件
    try:
        import matplotlib
        import numpy
        print("✅ 所需套件已安裝")
    except ImportError as e:
        print(f"❌ 缺少必要套件: {e}")
        print("請執行: pip install matplotlib numpy")
        return
    
    app = ESP32AudioVisualizer()
    app.run()

if __name__ == "__main__":
    main()
