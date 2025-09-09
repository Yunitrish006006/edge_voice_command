#include "wifi_manager.h"
#include "mqtt_manager.h"

// WiFi 設定
const char *ssid = "Yun";
const char *password = "0937565253";

// MQTT 設定
const char *mqtt_server = "10.109.91.204"; // 自建 MQTT broker IP
const int mqtt_port = 1883;
const char *client_id = "ESP32_Heartbeat_Test";

// 創建管理器實例
WiFiManager wifiManager(ssid, password);
MQTTConfig mqttConfig(mqtt_server, mqtt_port, client_id);
MQTTManager mqttManager(mqttConfig);

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("🚀 ESP32 MQTT 心跳測試");
    Serial.println("========================");

    // 連接 WiFi
    Serial.println("📶 正在連接 WiFi...");
    wifiManager.connect();

    if (!wifiManager.isConnected())
    {
        Serial.println("❌ WiFi 連接失敗");
        return;
    }

    // 初始化 MQTT
    Serial.println("📡 初始化 MQTT Manager...");
    mqttManager.begin();
    mqttManager.setAutoReconnect(true, 5000);

    // 連接 MQTT
    if (wifiManager.isConnected())
    {
        Serial.println("🔗 正在連接 MQTT Broker...");
        mqttManager.connect();
    }

    Serial.println("✅ 系統初始化完成");
    Serial.println("💓 開始心跳測試...");
}

void loop()
{
    // 檢查 WiFi 連接
    if (!wifiManager.isConnected())
    {
        Serial.println("📶 WiFi 連接失效，重新連接...");
        wifiManager.reconnect();
        return;
    }

    // 處理 MQTT 通訊和自動重連
    mqttManager.loop();

    // 每 10 秒發送一次心跳訊息 (測試用，頻率較高)
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat > 10000)
    {
        if (mqttManager.isConnected())
        {
            String heartbeat = "Heartbeat - " + String(millis() / 1000) + "s";
            bool result = mqttManager.publish("esp32/heartbeat", heartbeat.c_str());

            if (result)
            {
                Serial.println("💓 心跳發送成功: " + heartbeat);
            }
            else
            {
                Serial.println("❌ 心跳發送失敗");
            }
        }
        else
        {
            Serial.println("⚠️  MQTT 未連接，跳過心跳");
        }
        lastHeartbeat = millis();
    }

    delay(100);
}