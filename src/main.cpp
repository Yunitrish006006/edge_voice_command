#include "wifi_manager.h"
#include "mqtt_manager.h"

// const char *ssid = "CTC_Deco";
// const char *password = "53537826";

const char *mqtt_server = "192.168.1.121";
const int mqtt_port = 1883;
const char *client_id = "ESP32_Heartbeat_Test";

WiFiManager wifiManager("CTC_Deco", "53537826");
MQTTConfig mqttConfig(mqtt_server, mqtt_port, client_id);
MQTTManager mqttManager(mqttConfig, true);

void setup()
{
    Serial.begin(115200);
    delay(1000);
    wifiManager.connect();

    if (!wifiManager.isConnected())
        return;
    mqttManager.begin();
    mqttManager.setAutoReconnect(true, 5000);
    if (wifiManager.isConnected())
        mqttManager.connect();
}

void loop()
{
    if (!wifiManager.isConnected())
    {
        wifiManager.reconnect();
        return;
    }
    mqttManager.loop();
    delay(100);
}