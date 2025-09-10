#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <WiFi.h>
#include <PubSubClient.h>
#include <functional>

// MQTT 連接狀態枚舉
enum class MQTTConnectionState
{
    DISCONNECTED,
    CONNECTING,
    CONNECTED,
    CONNECTION_FAILED
};

// MQTT 配置結構
struct MQTTConfig
{
    const char *server;
    int port;
    const char *clientId;
    const char *username;
    const char *password;
    bool useCredentials;

    // 預設構造函數
    MQTTConfig(const char *srv, int prt, const char *id,
               const char *user = nullptr, const char *pass = nullptr)
        : server(srv), port(prt), clientId(id), username(user), password(pass),
          useCredentials(user != nullptr && pass != nullptr) {}
};

// 訊息回調函數類型定義
typedef std::function<void(char *topic, uint8_t *payload, unsigned int length)> MessageCallback;
typedef std::function<void(bool connected)> ConnectionCallback;

class MQTTManager
{
private:
    WiFiClient wifiClient;
    PubSubClient mqttClient;

    // 配置
    MQTTConfig config;
    bool debug_enabled;

    // 狀態管理
    MQTTConnectionState connectionState;
    unsigned long lastConnectionAttempt;
    unsigned long reconnectInterval;
    bool autoReconnect;

    // 回調函數
    MessageCallback messageCallback;
    ConnectionCallback connectionCallback;

    // 內部方法
    void onMQTTMessage(char *topic, uint8_t *payload, unsigned int length);
    static void staticMessageCallback(char *topic, uint8_t *payload, unsigned int length);
    static MQTTManager *instance; // 靜態實例指針

public:
    // 構造函數
    MQTTManager(const MQTTConfig &cfg, bool debug = false);

    // 基本 MQTT 操作
    bool begin();
    bool connect();
    void disconnect();
    bool isConnected();
    void loop();

    // 訊息操作
    bool publish(const char *topic, const char *message, bool retained = false);
    bool publish(const char *topic, const uint8_t *payload, unsigned int length, bool retained = false);
    bool subscribe(const char *topic, uint8_t qos = 0);
    bool unsubscribe(const char *topic);

    // 回調設定
    void setMessageCallback(MessageCallback callback);
    void setConnectionCallback(ConnectionCallback callback);

    // 狀態管理
    MQTTConnectionState getConnectionState();
    const char *getConnectionStateString();
    void setAutoReconnect(bool enable, unsigned long interval = 5000);

    // 配置管理
    void updateServer(const char *server, int port);
    void updateCredentials(const char *username, const char *password);

    // 診斷功能
    void printStatus();
    int getLastError();
    void setDebug(bool enable);
};

#endif // MQTT_MANAGER_H
