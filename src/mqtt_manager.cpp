#include "mqtt_manager.h"

// 靜態成員初始化
MQTTManager *MQTTManager::instance = nullptr;

MQTTManager::MQTTManager(const MQTTConfig &cfg)
    : config(cfg), mqttClient(wifiClient), connectionState(MQTTConnectionState::DISCONNECTED),
      lastConnectionAttempt(0), reconnectInterval(5000), autoReconnect(true)
{

    // 設定靜態實例指針
    instance = this;

    // 設定 MQTT 客戶端回調
    mqttClient.setCallback(staticMessageCallback);
}

bool MQTTManager::begin()
{
    // 設定 MQTT 伺服器
    mqttClient.setServer(config.server, config.port);

    Serial.println("📡 MQTT Manager 已初始化");
    Serial.printf("   伺服器: %s:%d\n", config.server, config.port);
    Serial.printf("   客戶端ID: %s\n", config.clientId);

    return true;
}

bool MQTTManager::connect()
{
    if (connectionState == MQTTConnectionState::CONNECTING)
    {
        return false; // 已在連接中
    }

    connectionState = MQTTConnectionState::CONNECTING;
    lastConnectionAttempt = millis();

    Serial.print("🔗 正在連接 MQTT Broker...");

    bool connected = false;

    if (config.useCredentials)
    {
        connected = mqttClient.connect(config.clientId, config.username, config.password);
    }
    else
    {
        connected = mqttClient.connect(config.clientId);
    }

    if (connected)
    {
        connectionState = MQTTConnectionState::CONNECTED;
        Serial.println(" ✅ 連接成功!");

        // 調用連接回調
        if (connectionCallback)
        {
            connectionCallback(true);
        }

        return true;
    }
    else
    {
        connectionState = MQTTConnectionState::CONNECTION_FAILED;
        Serial.printf(" ❌ 連接失敗，錯誤代碼: %d\n", mqttClient.state());

        // 調用連接回調
        if (connectionCallback)
        {
            connectionCallback(false);
        }

        return false;
    }
}

void MQTTManager::disconnect()
{
    if (mqttClient.connected())
    {
        mqttClient.disconnect();
    }
    connectionState = MQTTConnectionState::DISCONNECTED;
    Serial.println("🔌 MQTT 已斷開連接");

    // 調用連接回調
    if (connectionCallback)
    {
        connectionCallback(false);
    }
}

bool MQTTManager::isConnected()
{
    return mqttClient.connected() && (connectionState == MQTTConnectionState::CONNECTED);
}

void MQTTManager::loop()
{
    // 處理 MQTT 通訊
    if (mqttClient.connected())
    {
        mqttClient.loop();
    }
    else if (connectionState == MQTTConnectionState::CONNECTED)
    {
        // 連接意外斷開
        connectionState = MQTTConnectionState::DISCONNECTED;
        Serial.println("⚠️  MQTT 連接意外斷開");

        if (connectionCallback)
        {
            connectionCallback(false);
        }
    }

    // 自動重連邏輯
    if (autoReconnect && !isConnected() &&
        connectionState != MQTTConnectionState::CONNECTING &&
        (millis() - lastConnectionAttempt > reconnectInterval))
    {

        connect();
    }
}

bool MQTTManager::publish(const char *topic, const char *message, bool retained)
{
    if (!isConnected())
    {
        Serial.println("❌ MQTT 未連接，無法發送訊息");
        return false;
    }

    bool result = mqttClient.publish(topic, message, retained);

    if (result)
    {
        Serial.printf("📤 訊息已發送到 %s: %s\n", topic, message);
    }
    else
    {
        Serial.printf("❌ 訊息發送失敗到 %s\n", topic);
    }

    return result;
}

bool MQTTManager::publish(const char *topic, const uint8_t *payload, unsigned int length, bool retained)
{
    if (!isConnected())
    {
        Serial.println("❌ MQTT 未連接，無法發送訊息");
        return false;
    }

    bool result = mqttClient.publish(topic, payload, length, retained);

    if (result)
    {
        Serial.printf("📤 二進制訊息已發送到 %s (%d bytes)\n", topic, length);
    }
    else
    {
        Serial.printf("❌ 二進制訊息發送失敗到 %s\n", topic);
    }

    return result;
}

bool MQTTManager::subscribe(const char *topic, uint8_t qos)
{
    if (!isConnected())
    {
        Serial.println("❌ MQTT 未連接，無法訂閱");
        return false;
    }

    bool result = mqttClient.subscribe(topic, qos);

    if (result)
    {
        Serial.printf("📬 已訂閱主題: %s (QoS: %d)\n", topic, qos);
    }
    else
    {
        Serial.printf("❌ 訂閱失敗: %s\n", topic);
    }

    return result;
}

bool MQTTManager::unsubscribe(const char *topic)
{
    if (!isConnected())
    {
        return false;
    }

    bool result = mqttClient.unsubscribe(topic);

    if (result)
    {
        Serial.printf("📪 已取消訂閱: %s\n", topic);
    }
    else
    {
        Serial.printf("❌ 取消訂閱失敗: %s\n", topic);
    }

    return result;
}

void MQTTManager::setMessageCallback(MessageCallback callback)
{
    messageCallback = callback;
}

void MQTTManager::setConnectionCallback(ConnectionCallback callback)
{
    connectionCallback = callback;
}

MQTTConnectionState MQTTManager::getConnectionState()
{
    return connectionState;
}

const char *MQTTManager::getConnectionStateString()
{
    switch (connectionState)
    {
    case MQTTConnectionState::DISCONNECTED:
        return "已斷開";
    case MQTTConnectionState::CONNECTING:
        return "連接中";
    case MQTTConnectionState::CONNECTED:
        return "已連接";
    case MQTTConnectionState::CONNECTION_FAILED:
        return "連接失敗";
    default:
        return "未知狀態";
    }
}

void MQTTManager::setAutoReconnect(bool enable, unsigned long interval)
{
    autoReconnect = enable;
    reconnectInterval = interval;

    Serial.printf("🔄 自動重連: %s (間隔: %lu ms)\n",
                  enable ? "啟用" : "停用", interval);
}

void MQTTManager::updateServer(const char *server, int port)
{
    config.server = server;
    config.port = port;

    mqttClient.setServer(server, port);

    Serial.printf("🔧 更新伺服器設定: %s:%d\n", server, port);
}

void MQTTManager::updateCredentials(const char *username, const char *password)
{
    config.username = username;
    config.password = password;
    config.useCredentials = (username != nullptr && password != nullptr);

    Serial.printf("🔐 更新認證設定: %s\n",
                  config.useCredentials ? "已啟用" : "已停用");
}

void MQTTManager::printStatus()
{
    Serial.println("📊 MQTT Manager 狀態:");
    Serial.printf("   伺服器: %s:%d\n", config.server, config.port);
    Serial.printf("   客戶端ID: %s\n", config.clientId);
    Serial.printf("   連接狀態: %s\n", getConnectionStateString());
    Serial.printf("   自動重連: %s\n", autoReconnect ? "啟用" : "停用");

    if (isConnected())
    {
        Serial.println("   ✅ MQTT 服務正常");
    }
    else
    {
        Serial.printf("   ❌ 最後錯誤: %d\n", mqttClient.state());
    }
}

int MQTTManager::getLastError()
{
    return mqttClient.state();
}

// 靜態回調函數
void MQTTManager::staticMessageCallback(char *topic, uint8_t *payload, unsigned int length)
{
    if (instance && instance->messageCallback)
    {
        instance->messageCallback(topic, payload, length);
    }
}

// 內部訊息處理
void MQTTManager::onMQTTMessage(char *topic, uint8_t *payload, unsigned int length)
{
    // 轉換為字串
    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.printf("📨 收到訊息 [%s]: %s\n", topic, message);

    // 調用用戶回調
    if (messageCallback)
    {
        messageCallback(topic, payload, length);
    }
}
