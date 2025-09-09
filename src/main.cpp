#include "wifi_manager.h"
#include <PubSubClient.h>

// WiFi 設定
const char *ssid = "YUNROG";
const char *password = "0937565253";

// MQTT 設定
const char *mqtt_server = "192.168.98.106"; // 自建 MQTT broker IP
const int mqtt_port = 1883;
const char *mqtt_topic = "esp32/voice_command";
const char *client_id = "ESP32_Voice_Command";

// 創建 WiFi 管理器和 MQTT 客戶端
WiFiManager wifiManager(ssid, password);
WiFiClient espClient;
PubSubClient mqttClient(espClient);

// MQTT 連接函數
bool connectMQTT()
{
    if (mqttClient.connect(client_id))
    {
        return true;
    }
    return false;
}

// MQTT 發送訊息函數
bool sendMQTTMessage(const char *message)
{
    if (mqttClient.connected())
    {
        return mqttClient.publish(mqtt_topic, message);
    }
    return false;
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    // 連接 WiFi
    wifiManager.connect();

    // 設定 MQTT 伺服器
    mqttClient.setServer(mqtt_server, mqtt_port);

    // 連接 MQTT
    if (wifiManager.isConnected())
    {
        connectMQTT();
    }
}

void loop()
{
    // 檢查 WiFi 連接
    if (!wifiManager.isConnected())
    {
        wifiManager.reconnect();
        return;
    }

    // 檢查 MQTT 連接
    if (!mqttClient.connected())
    {
        connectMQTT();
    }

    // 保持 MQTT 連接
    mqttClient.loop();

    // 每 30 秒發送一次測試訊息
    static unsigned long lastSend = 0;
    if (millis() - lastSend > 30000)
    {
        String message = "Hello from ESP32-S3 at " + String(millis());
        sendMQTTMessage(message.c_str());
        lastSend = millis();
    }

    delay(1000);
}