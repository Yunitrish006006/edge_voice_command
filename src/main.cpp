#include "wifi_manager.h"
#include "mqtt_manager.h"

// MQTT 設定
const char *mqtt_server = "192.168.1.121";
const int mqtt_port = 1883;
const char *client_id = "ESP32_Voice_Command";

// 創建管理器實例
WiFiManager wifiManager("CTC_Deco", "53537826");
MQTTConfig mqttConfig(mqtt_server, mqtt_port, client_id);
MQTTManager mqttManager(mqttConfig, true);

// 函數聲明
void handleCommand(String command);
void handleConfig(String topic, String value);
void onMQTTMessage(char *topic, uint8_t *payload, unsigned int length);
void onMQTTConnect(bool connected);

// MQTT 訊息回調函數
void onMQTTMessage(char *topic, uint8_t *payload, unsigned int length)
{
    // 轉換 payload 為字串
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.printf("📨 收到訊息 [%s]: %s\n", topic, message);

    // 處理不同主題的訊息
    String topicStr = String(topic);
    String messageStr = String(message);

    if (topicStr == "esp32/command")
    {
        Serial.printf("🎯 處理指令: %s\n", message);
        handleCommand(messageStr);
    }
    else if (topicStr.startsWith("esp32/config/"))
    {
        Serial.printf("⚙️ 處理配置: %s\n", message);
        handleConfig(topicStr, messageStr);
    }
    else
    {
        Serial.printf("📋 未處理的主題: %s\n", topic);
    }
}

// 指令處理函數
void handleCommand(String command)
{
    command.toLowerCase();

    if (command == "ping")
    {
        mqttManager.publish("esp32/response", "pong");
        Serial.println("🏓 回應 ping 指令");
    }
    else if (command == "status")
    {
        String status = "WiFi: " + String(wifiManager.isConnected() ? "已連接" : "斷開") +
                        ", MQTT: " + String(mqttManager.isConnected() ? "已連接" : "斷開");
        mqttManager.publish("esp32/response", status.c_str());
        Serial.println("📊 回應狀態查詢");
    }
    else if (command == "restart")
    {
        mqttManager.publish("esp32/response", "重新啟動中...");
        Serial.println("🔄 執行重新啟動");
        delay(1000);
        ESP.restart();
    }
    else
    {
        String response = "未知指令: " + command;
        mqttManager.publish("esp32/response", response.c_str());
        Serial.printf("❓ 未知指令: %s\n", command.c_str());
    }
}

// 配置處理函數
void handleConfig(String topic, String value)
{
    if (topic == "esp32/config/debug")
    {
        bool enableDebug = (value == "true" || value == "1");
        wifiManager.setDebug(enableDebug);
        mqttManager.setDebug(enableDebug);

        String response = "Debug模式: " + String(enableDebug ? "已啟用" : "已停用");
        mqttManager.publish("esp32/response", response.c_str());
        Serial.printf("🔧 設定Debug模式: %s\n", enableDebug ? "啟用" : "停用");
    }
    else
    {
        String response = "未知配置: " + topic;
        mqttManager.publish("esp32/response", response.c_str());
        Serial.printf("❓ 未知配置: %s\n", topic.c_str());
    }
}

// 連接回調函數
void onMQTTConnect(bool connected)
{
    if (connected)
    {
        Serial.println("🔗 MQTT 連接成功，開始訂閱主題...");

        // 訂閱指令主題
        mqttManager.subscribe("esp32/command");

        // 訂閱配置主題 (使用通配符)
        mqttManager.subscribe("esp32/config/+");

        // 發送上線通知
        mqttManager.publish("esp32/status", "online", true);

        Serial.println("✅ 主題訂閱完成");
    }
    else
    {
        Serial.println("❌ MQTT 連接斷開");
    }
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("🚀 ESP32 系統啟動");

    wifiManager.connect();
    if (!wifiManager.isConnected())
    {
        return;
    }

    mqttManager.setMessageCallback(onMQTTMessage);
    mqttManager.setConnectionCallback(onMQTTConnect);

    mqttManager.begin();
    mqttManager.setAutoReconnect(true, 5000);

    if (wifiManager.isConnected())
    {
        mqttManager.connect();
    }

    Serial.println("🎧 系統就緒");
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