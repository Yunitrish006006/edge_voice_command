#include "wifi_manager.h"

WiFiManager::WiFiManager(const char *ssid, const char *password, bool debug)
{
    this->ssid = ssid;
    this->password = password;
    this->debug_enabled = debug;
}

bool WiFiManager::connect()
{
    if (debug_enabled)
    {
        Serial.println("[WiFi Debug] 開始連接到 WiFi...");
        Serial.print("[WiFi Debug] SSID: ");
        Serial.println(ssid);
    }

    WiFi.begin(ssid, password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20)
    {
        delay(500);
        attempts++;

        if (debug_enabled)
        {
            Serial.print("[WiFi Debug] 連接嘗試 ");
            Serial.print(attempts);
            Serial.print("/20, 狀態: ");
            Serial.println(WiFi.status());
        }
    }

    bool connected = WiFi.status() == WL_CONNECTED;

    if (debug_enabled)
    {
        if (connected)
        {
            Serial.println("[WiFi Debug] ✅ WiFi 連接成功!");
            Serial.print("[WiFi Debug] IP 位址: ");
            Serial.println(WiFi.localIP());
            Serial.print("[WiFi Debug] 信號強度: ");
            Serial.print(WiFi.RSSI());
            Serial.println(" dBm");
        }
        else
        {
            Serial.println("[WiFi Debug] ❌ WiFi 連接失敗!");
        }
    }

    return connected;
}

bool WiFiManager::isConnected()
{
    return WiFi.status() == WL_CONNECTED;
}

void WiFiManager::reconnect()
{
    if (debug_enabled)
    {
        Serial.println("[WiFi Debug] 嘗試重新連接 WiFi...");
    }

    WiFi.reconnect();

    if (debug_enabled)
    {
        Serial.print("[WiFi Debug] 重新連接狀態: ");
        Serial.println(WiFi.status());
    }
}

void WiFiManager::printStatus()
{
    if (isConnected())
    {
        Serial.print("IP 位址: ");
        Serial.println(WiFi.localIP());
        Serial.print("信號強度: ");
        Serial.print(WiFi.RSSI());
        Serial.println(" dBm");
        Serial.print("MAC 位址: ");
        Serial.println(WiFi.macAddress());
    }
    else
    {
        Serial.println("WiFi 未連接");
    }
}

String WiFiManager::getIP()
{
    return WiFi.localIP().toString();
}

int WiFiManager::getRSSI()
{
    return WiFi.RSSI();
}

String WiFiManager::getMAC()
{
    return WiFi.macAddress();
}

void WiFiManager::setDebug(bool enable)
{
    debug_enabled = enable;
    if (debug_enabled)
    {
        Serial.println("[WiFi Debug] WiFi 除錯模式已啟用");
    }
}
