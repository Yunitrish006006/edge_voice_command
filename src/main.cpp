#include "wifi_manager.h"

// WiFi 設定
const char *ssid = "YUNROG";
const char *password = "0937565253";

// 創建 WiFi 管理器
WiFiManager wifiManager(ssid, password);

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println();
    Serial.println("ESP32-S3 WiFi 連接測試");
    Serial.println("========================");

    // 連接 WiFi
    wifiManager.connect();
}

void loop()
{
    if (wifiManager.isConnected())
    {
        Serial.print("連接正常 - IP: ");
        Serial.print(wifiManager.getIP());
        Serial.print(" | 信號: ");
        Serial.print(wifiManager.getRSSI());
        Serial.println(" dBm");
    }
    else
    {
        Serial.println("WiFi 連接中斷，嘗試重新連接...");
        wifiManager.reconnect();
    }

    delay(10000); // 等待 10 秒
}