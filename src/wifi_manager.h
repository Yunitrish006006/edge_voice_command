#ifndef WIFI_MANAGER_H
#define WIFI_MANAGER_H

#include <WiFi.h>

class WiFiManager
{
private:
    const char *ssid;
    const char *password;
    bool debug_enabled;

public:
    WiFiManager(const char *ssid, const char *password, bool debug = false);
    bool connect();
    bool isConnected();
    void reconnect();
    void printStatus();
    String getIP();
    int getRSSI();
    String getMAC();
    void setDebug(bool enable);
};

#endif
