# 邊緣端語音指令系統 — 系統架構圖（ESP32‑S3 + MQTT + 蒸餾）

下圖描述端‑雲協作的資料流、MQTT 主題與訓練/更新循環。

```mermaid
flowchart LR
  %% 端側
  mic[INMP441 麥克風]
  esp[ESP32‑S3\nVAD/特徵(log‑Mel)\n學生模型(KWS)\nMQTT Client]
  mic --> esp

  %% MQTT
  subgraph broker[MQTT Broker GUI]
    direction TB
    b[(Broker)]
  end

  %% 伺服器
  subgraph srv[伺服器端]
    direction TB
    featS[Feature Server\n訂閱 esp32/feat/#\n回覆 esp32/infer/{device}]
    train[教師模型 + 週期性蒸餾(QAT)\n產生 int8 學生模型]
    ota[模型發佈/OTA\n控制訊息 esp32/control/{device}]
  end

  %% 監控
  mon[監控 Client GUI\n訂閱 esp32/#]

  %% 資料流
  esp -- 上傳特徵\nesp32/feat/{device}/{session}/{idx} --> b
  b --> featS
  featS -- 推論結果\nesp32/infer/{device} --> b --> esp

  %% 控制/狀態
  esp -- 上線/心跳\nesp32/status/{device} --> b --> mon
  ota -- 模型/參數下發\nesp32/control/{device} --> b --> esp

  %% 訓練循環
  featS -. 蒐集樣本/標記 .-> train
  train --> ota

  %% 可選：原音分塊
  esp -- (可選)音訊塊\nesp32/audio/{ts}/{chunk} --> b --> mon
```

關鍵主題（可於 `python/config.py` 調整）
- 特徵上傳：`esp32/feat/{device}/{session}/{idx}`
- 推論回覆：`esp32/infer/{device}`
- 控制下發：`esp32/control/{device}`
- 狀態心跳：`esp32/status/{device}`
- （可選）音訊塊：`esp32/audio/{timestamp}/{chunk}`

對應元件
- 端側：`src/main.cpp`、`src/audio_manager.*`
- Broker GUI：`python/mqtt_broker_gui.py`
- 監控 GUI：`python/mqtt_client_gui.py`
- 特徵伺服器：`python/feature_server.py`
- 特徵模擬器：`python/feature_simulator.py`
- 方法論：`docs/methodology_zh.md`

