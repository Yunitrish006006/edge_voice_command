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

    // 連接 WiFi
    wifiManager.connect();
}

void loop()
{
    if (!wifiManager.isConnected())
    {
        wifiManager.reconnect();
    }

    delay(10000); // 等待 10 秒
}