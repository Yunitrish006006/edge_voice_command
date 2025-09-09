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
    Serial.print("正在連接 MQTT...");
    if (mqttClient.connect(client_id))
    {
        Serial.println(" 成功!");
        return true;
    }
    else
    {
        Serial.print(" 失敗，錯誤代碼: ");
        Serial.println(mqttClient.state());
        return false;
    }
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
        Serial.println("WiFi 連接失效，重新連接...");
        wifiManager.reconnect();
        return;
    }

    // 檢查 MQTT 連接
    if (!mqttClient.connected())
    {
        Serial.println("MQTT 連接失效，重新連接...");
        static unsigned long lastMQTTAttempt = 0;
        if (millis() - lastMQTTAttempt > 5000) // 每5秒嘗試一次
        {
            lastMQTTAttempt = millis();
            connectMQTT();
        }
        return; // 如果 MQTT 未連接，不執行其他操作
    }

    // 保持 MQTT 連接
    mqttClient.loop();

    // 每 30 秒發送一次測試訊息
    static unsigned long lastSend = 0;
    if (millis() - lastSend > 30000)
    {
        String message = "Hello from ESP32-S3 at " + String(millis());
        if (sendMQTTMessage(message.c_str()))
        {
            Serial.println("訊息發送成功: " + message);
        }
        else
        {
            Serial.println("訊息發送失敗");
        }
        lastSend = millis();
    }

    delay(1000);
}