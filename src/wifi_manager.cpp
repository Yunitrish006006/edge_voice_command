#include "wifi_manager.h"

WiFiManager::WiFiManager(const char *ssid, const char *password)
{
    this->ssid = ssid;
    this->password = password;
}

bool WiFiManager::connect()
{
    Serial.println("正在連接 WiFi...");
    WiFi.begin(ssid, password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20)
    {
        delay(500);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED)
    {
        Serial.println();
        Serial.println("WiFi 連接成功!");
        printStatus();
        return true;
    }
    else
    {
        Serial.println();
        Serial.println("WiFi 連接失敗!");
        return false;
    }
}

bool WiFiManager::isConnected()
{
    return WiFi.status() == WL_CONNECTED;
}

void WiFiManager::reconnect()
{
    Serial.println("嘗試重新連接 WiFi...");
    WiFi.reconnect();
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
