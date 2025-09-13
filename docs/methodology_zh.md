# 邊緣端語音指令系統：方法論與簡報大綱（ESP32‑S3 + INMP441 + MQTT + 知識蒸餾）

## 1. 研究目標與貢獻
- 邊緣端（ESP32‑S3）以低功耗、低延遲執行語音指令（KWS/短指令）。
- 以特徵上傳（log‑Mel/MFCC）取代原始音訊，降低上行頻寬與隱私風險。
- 雲/伺服器端以教師模型週期性蒸餾，產生輕量學生模型回灌至裝置。
- 建立以 MQTT 為核心的資料、模型與指令通道，支援在線監控與 OTA 更新。

## 2. 系統架構（端‑雲協作）
- 邊緣端（ESP32‑S3 + INMP441）
  - 以 I2S 16 kHz 單聲道錄音，前處理（增益/去直流/簡單 AGC）。
  - VAD（能量/零交越或輕量 WebRTC VAD），決定上傳時機與段落。
  - 特徵提取：log‑Mel 或 MFCC，支援 int8/uint8 量化後上傳。
  - 本地學生模型（如 DS‑CNN/Tiny‑CNN）推論快速指令；失敗或低信心時上傳特徵至伺服器。
- MQTT Broker + 伺服器端
  - 接收特徵/狀態，回傳推論結果與控制命令。
  - 教師模型（較大 CNN/CRNN/Conformer 小型版）離線或週期性訓練。
  - 知識蒸餾 + 量化感知訓練（QAT）→ 輕量學生模型（int8）→ OTA 更新。

## 3. 資料流與 MQTT Topic 設計
- 狀態/心跳：`esp32/status/{device_id}` JSON
  - {"fw":"1.0.2","uptime":1234,"mem_kb":220,"rssi":-55}
- 指令下發：`esp32/control/{device_id}` JSON
  - 類型示例：{"type":"model_update","version":"2025.01","checksum":"...","url":"http://.../kws.bin"}
  - 其他：{"type":"set_threshold","value":0.75}、{"type":"reboot"}
- 推論結果上報：`esp32/infer/{device_id}` JSON
  - {"ts":...,"result":"yes","conf":0.91,"latency_ms":37}
- 特徵上傳（流式）：`esp32/feat/{device_id}/{session_id}/{frame_idx}` Binary 或 Base64 JSON
  - 建議 JSON：
    {"ts":...,"sr":16000,"feat":"logmel","shape":[T,F],"win_ms":25,"hop_ms":10,"q":"u8","data":"<base64>"}
- 音訊塊（若需原始音）：沿用現有 `esp32/audio/<timestamp>/<chunk_idx>` 與 `esp32/audio/info`

QoS 建議：
- 控制/模型更新用 QoS 1；特徵流可 QoS 0/1 視網路品質。
- Retain 僅用於最新模型版本公告。

## 4. 邊緣側特徵與推論設計（ESP32‑S3）
- 取樣與分幀：16 kHz、單聲道，窗長 25 ms、移動 10 ms，漢明窗。
- 濾波銀行：40 或 64 個 Mel 濾波器，取 log 能量（或再做 DCT 取前 13 個 MFCC + Δ/ΔΔ）。
- 正規化：在線均值方差或每段 z‑score；固定縮放至 [0,255] 以便 u8 量化。
- VAD：短時能量門檻 + 持續長度約束；VAD=1 的幀才上傳/推論。
- 學生模型備選：
  - DS‑CNN（depthwise separable CNN）或 Tiny‑CNN（2‑4 層）輸入 2D 時頻圖。
  - 參考算力：< 50k 參數，SRAM < 200 KB，Flash < 500 KB，單次 < 30 ms。
- 量化部署：
  - 訓練階段使用 QAT；導出 int8（權重+激活）。
  - ESP‑DSP/ESP‑NN 或 TFLM（若走 TFLite Micro）以加速卷積。

## 5. 伺服器端訓練與週期性知識蒸餾
- 基礎資料：Google Speech Commands v2（或自建指令集），類別 10‑35 類。
- 教師模型：
  - 較大 CNN/CRNN 或小型 Conformer；輸入 log‑Mel 序列；精度基準高於學生。
- 蒸餾流程（每日/每週）：
  1) 整理資料：歷史資料 + 新收集特徵（可匿名化）。
  2) 教師產生軟標籤：p_T = softmax(z_T / T)，溫度 T=2‑4。
  3) 學生最小化 L = CE(y_s, y_gt) + α·T^2·KL(p_T || p_s)。
  4) QAT：插入 FakeQuant 節點，維持部署分佈一致性。
  5) 驗證：裝置代表集與延遲/RAM/功耗評估，通過閾值才釋出。
- 模型釋出與 OTA：
  - 以 MQTT 發佈新模型版本公告 + 下載 URL；裝置以分塊/校驗更新，預留 A/B 回滾機制。

## 6. 評估指標與實驗設計
- 模型效能：Top‑1 準確率、F1、混淆矩陣（少數類重加權）。
- 邊緣表現：
  - 延遲：前處理 + 推論（P50/P95）；吞吐：每秒可處理段數。
  - 資源：SRAM 峰值、Flash 佔用、運算週期（ESP‑IDF perf counter）。
  - 能耗：以電流記錄器或估算（活動/待機/VAD門檻對比）。
- 網路開銷：特徵平均上行（bytes/s），不同 hop/window/量化下的對比。
- 蒸餾收益：與非蒸餾小模型、僅量化模型之對比；不同溫度/α 的消融實驗。
- 數據隱私：特徵 vs 原音上傳的重建風險（簡評）。

## 7. 初步 PoC 與 Demo（對齊你現有程式）
- 既有：
  - 本地 MQTT Broker GUI：`python/mqtt_broker_gui.py`
  - 客戶端監控 GUI：`python/mqtt_client_gui.py`
  - 音訊塊接收器：`python/audio_data_receiver.py`（主題：`esp32/audio/...`）
- 新增（本 repo 提供）：
  - `python/feature_simulator.py`：模擬裝置上傳特徵（`esp32/feat/<device>/<session>/<frame>`）。
- Demo 步驟：
  1) 啟動 Broker GUI，確認監聽位址與埠。
  2) 啟動監控 GUI，訂閱 `esp32/#`。
  3) 執行 `feature_simulator.py` 發送假資料；觀察特徵訊息與格式。
  4) 若要測試音訊塊，另啟 `audio_data_receiver.py`，並從 ESP32 發送錄音塊。

## 8. 風險與對策
- 網路抖動/封包遺失：特徵分片 + 序號 + 會話 ID；QoS 1 於關鍵通道。
- 隱私：預設僅上傳特徵且可匿名化；敏感場合關閉原音上傳。
- 模型回滾：A/B 分區與版本檢查；更新失敗自動回退。
- 漂移：教師偵測資料分佈變化；低信心樣本入庫再訓練。
- 裝置異質：多學生模型配置檔，依 SRAM/Flash 自動選型。

## 9. 里程碑與時程（示例，8–12 週）
- W1‑2：端側特徵與 VAD 原型、MQTT 主題與訊息規格凍結。
- W3‑4：教師/學生初版模型、基準測試（精度/延遲/資源）。
- W5‑6：QAT + 蒸餾穩定、ESP32 部署與本地推論穩定。
- W7‑8：週期性訓練管線與 OTA；端‑雲回路打通。
- W9‑10：實驗與消融；撰寫論文初稿與 Demo 錄影。
- W11‑12：潤稿與口試準備。

## 10. 簡報/報告大綱（10–12 頁）
1) 動機與目標（邊緣 KWS 挑戰、頻寬/隱私）
2) 系統架構圖（端‑雲、MQTT 通道）
3) 特徵選型與端側前處理（VAD、量化）
4) 教師‑學生與蒸餾損失（公式與直觀）
5) 訓練與更新管線（排程、驗證、OTA）
6) MQTT Topic/負載格式（可直接貼本文件章節）
7) 實驗設計與評估指標
8) 初步結果或預期效益（估算表）
9) 風險與對策
10) 時程與 Demo 設計

——
附：最小訊息格式（示例）

- 上傳特徵 `esp32/feat/{device}/{session}/{idx}`：
  {
    "ts": 1736812345678,
    "sr": 16000,
    "feat": "logmel",
    "shape": [10, 40],
    "win_ms": 25,
    "hop_ms": 10,
    "q": "u8",
    "data": "BASE64..."
  }

- 伺服器回推結果 `esp32/infer/{device}`：
  {"ts": 1736812345688, "result": "on", "conf": 0.92}

- 模型更新 `esp32/control/{device}`：
  {"type":"model_update","version":"2025.01","url":"http://.../kws.bin","checksum":"..."}

