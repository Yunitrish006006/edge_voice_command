# esp32

## esp32-s3-wroom-1

![esp32 pinout](pinout.jpg "esp32-s3-wroom-1")

## 語音模組

| Pin     | 功能                  | 說明                                      |
| ------- | ------------------- | --------------------------------------- |
| **VDD** | 電源正極                | 通常 3.3 V（部分型號支援 1.8V\~3.6V，要查資料表確認）     |
| **GND** | 地線                  | 電源與信號地                                  |
| **SD**  | Serial Data         | I²S 數據輸出（麥克風的音訊資料）                      |
| **WS**  | Word Select (LRCLK) | I²S 左/右聲道時脈，用於同步數據                      |
| **SCK** | Serial Clock (BCLK) | I²S 位元時脈，控制數據傳輸速率                       |
| **L/R** | Left/Right Select   | 選擇此麥克風輸出的聲道（接 GND=左聲道，接 VDD=右聲道，部分模組反之） |
