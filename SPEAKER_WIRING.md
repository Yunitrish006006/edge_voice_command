# 🔊 ESP32-S3 喇叭接線圖

## 📌 喇叭接腳對應

### ESP32-S3 ➜ I2S 喇叭模組

```
喇叭接腳    ←→   ESP32-S3 GPIO    說明
─────────────────────────────────────────
LRC         ←→   GPIO 15          左右聲道時脈 (WS)
BCLK        ←→   GPIO 14          位元時脈
DIN         ←→   GPIO 13          數據輸入
GAIN        ←→   GPIO 12          增益控制 (PWM)
SD          ←→   GPIO 11          啟用/關閉控制
GND         ←→   GND              地線
VIN         ←→   5V/3.3V          電源 (根據模組需求)
```

## 🔧 接線步驟

### 1. I2S 音訊信號

- **LRC (GPIO15)**: 左右聲道時脈信號
- **BCLK (GPIO14)**: 位元時脈信號  
- **DIN (GPIO13)**: 立體聲音訊數據

### 2. 控制信號

- **GAIN (GPIO12)**: PWM 控制增益 (0-255)
- **SD (GPIO11)**: 喇叭啟用控制 (HIGH=啟用, LOW=關閉)

### 3. 電源

- **VIN**: 連接到適當電壓 (通常 3.3V 或 5V)
- **GND**: 接地

## 🎵 MQTT 控制指令

### 基本播放指令

```bash
# 播放提示音 (200ms)
mosquitto_pub -h localhost -t "esp32/command" -m "play_beep"

# 播放警報聲 (1000ms)  
mosquitto_pub -h localhost -t "esp32/command" -m "play_alarm"

# 播放旋律
mosquitto_pub -h localhost -t "esp32/command" -m "play_melody"

# 喇叭狀態
mosquitto_pub -h localhost -t "esp32/command" -m "speaker_status"
```

### 喇叭控制指令

```bash
# 啟用喇叭擴音器
mosquitto_pub -h localhost -t "esp32/command" -m "speaker_enable"

# 關閉喇叭擴音器  
mosquitto_pub -h localhost -t "esp32/command" -m "speaker_disable"
```

### 配置指令

```bash
# 設定軟體音量 (0.0-1.0)
mosquitto_pub -h localhost -t "esp32/config/speaker_volume" -m "0.8"

# 設定硬體增益 (0-255)
mosquitto_pub -h localhost -t "esp32/config/speaker_gain" -m "128"

# 播放自訂音調 (頻率Hz,持續時間ms)
mosquitto_pub -h localhost -t "esp32/config/play_tone" -m "1000,500"
```

## 🔍 診斷功能

### 檢查喇叭狀態

```bash
mosquitto_pub -h localhost -t "esp32/command" -m "speaker_status"
```

輸出包含:

- 初始化狀態
- 播放狀態  
- 音量設定
- GPIO 配置
- 擴音器狀態

## ⚡ 系統特色

### 🎯 音訊功能

- **16kHz 取樣率** 立體聲輸出
- **動態音調生成** 支援任意頻率
- **旋律播放** 多音符序列
- **警報音效** 內建警報模式

### 🎛️ 硬體控制

- **PWM 增益控制** 精確調整硬體增益
- **擴音器開關** 節能控制
- **雙重音量控制** 軟體+硬體調節

### 📡 MQTT 整合

- **即時控制** 遠端播放控制
- **參數配置** 動態調整設定
- **狀態回報** 完整診斷資訊

## 🚀 啟動程序

1. **連接硬體** 根據接線圖連接喇叭
2. **燒錄韌體** 上傳編譯好的程式
3. **啟動 MQTT** 確保 broker 運行
4. **測試播放** 發送播放指令
5. **調整設定** 根據需求微調

## 📊 記憶體使用

- **RAM**: 16.3% (53,348 / 327,680 bytes)  
- **Flash**: 23.2% (774,029 / 3,342,336 bytes)

## ⚠️ 注意事項

1. **電源需求**: 確保喇叭模組電源需求
2. **GPIO 衝突**: 避免與麥克風 GPIO 重複
3. **音量控制**: 避免過大音量損壞喇叭
4. **接地良好**: 確保 GND 連接穩固

---
*最後更新: 2025-09-10*
