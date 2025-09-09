#include "wifi_manager.h"

WiFiManager::WiFiManager(const char *ssid, const char *password)
{
    this->ssid = ssid;
    this->password = password;
}

bool WiFiManager::connect()
{
    WiFi.begin(ssid, password);

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 20)
    {
        delay(500);
        attempts++;
    }

    return WiFi.status() == WL_CONNECTED;
}

bool WiFiManager::isConnected()
{
    return WiFi.status() == WL_CONNECTED;
}

void WiFiManager::reconnect()
{
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
