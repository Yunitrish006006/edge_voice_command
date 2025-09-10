#include "wifi_manager.h"
#include "mqtt_manager.h"
#include "audio_manager.h"
#include "speaker_manager.h"

// MQTT 設定
const char *mqtt_server = "192.168.98.106";
const int mqtt_port = 1883;
const char *client_id = "ESP32_Voice_Command";

// 創建管理器實例
WiFiManager wifiManager("YUNROG", "0937565253");
MQTTConfig mqttConfig(mqtt_server, mqtt_port, client_id);
MQTTManager mqttManager(mqttConfig, false); // 關閉MQTT debug減少輸出
AudioManager audioManager(false);           // 關閉音訊debug
SpeakerManager speakerManager(true);        // 啟用喇叭debug

// 函數聲明
void handleCommand(String command);
void handleConfig(String topic, String value);
void onMQTTMessage(char *topic, uint8_t *payload, unsigned int length);
void onMQTTConnect(bool connected);
void onAudioData(float volume, float *frequencies, int freqCount);

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
                        ", MQTT: " + String(mqttManager.isConnected() ? "已連接" : "斷開") +
                        ", Audio: " + String(audioManager.isRecording() ? "錄音中" : "停止");
        mqttManager.publish("esp32/response", status.c_str());
        Serial.println("📊 回應狀態查詢");
    }
    else if (command == "start_audio")
    {
        if (audioManager.startRecording())
        {
            mqttManager.publish("esp32/response", "音訊錄製已開始");
            Serial.println("🎙️ 開始音訊錄製");
        }
        else
        {
            mqttManager.publish("esp32/response", "音訊錄製啟動失敗");
            Serial.println("❌ 音訊錄製啟動失敗");
        }
    }
    else if (command == "stop_audio")
    {
        audioManager.stopRecording();
        mqttManager.publish("esp32/response", "音訊錄製已停止");
        Serial.println("⏹️ 停止音訊錄製");
    }
    else if (command == "audio_status")
    {
        audioManager.printStatus();
        String audioStatus = String("Volume: ") + String(audioManager.getCurrentVolume(), 3) +
                             ", Recording: " + String(audioManager.isRecording() ? "Yes" : "No");
        mqttManager.publish("esp32/audio", audioStatus.c_str());
    }
    else if (command == "play_beep")
    {
        if (speakerManager.playBeep(500))
        {
            mqttManager.publish("esp32/response", "播放嗶聲");
            Serial.println("🔊 播放嗶聲");
        }
        else
        {
            mqttManager.publish("esp32/response", "嗶聲播放失敗");
            Serial.println("❌ 嗶聲播放失敗");
        }
    }
    else if (command == "play_alarm")
    {
        if (speakerManager.playAlarm(2000))
        {
            mqttManager.publish("esp32/response", "播放警報聲");
            Serial.println("🚨 播放警報聲");
        }
        else
        {
            mqttManager.publish("esp32/response", "警報聲播放失敗");
            Serial.println("❌ 警報聲播放失敗");
        }
    }
    else if (command == "play_melody")
    {
        // 播放簡單旋律 (Do Re Mi Fa Sol)
        float frequencies[] = {261.63, 293.66, 329.63, 349.23, 392.00}; // C D E F G
        int durations[] = {400, 400, 400, 400, 800};

        if (speakerManager.playMelody(frequencies, durations, 5))
        {
            mqttManager.publish("esp32/response", "播放旋律");
            Serial.println("🎵 播放旋律");
        }
        else
        {
            mqttManager.publish("esp32/response", "旋律播放失敗");
            Serial.println("❌ 旋律播放失敗");
        }
    }
    else if (command == "speaker_status")
    {
        speakerManager.printStatus();
        String speakerStatus = String("Volume: ") + String(speakerManager.getVolume(), 2) +
                               ", Playing: " + String(speakerManager.isPlaying() ? "Yes" : "No");
        mqttManager.publish("esp32/speaker", speakerStatus.c_str());
    }
    else if (command == "speaker_enable")
    {
        speakerManager.enableAmplifier(true);
        mqttManager.publish("esp32/response", "喇叭擴音器已啟用");
        Serial.println("🔊 喇叭擴音器已啟用");
    }
    else if (command == "speaker_disable")
    {
        speakerManager.enableAmplifier(false);
        mqttManager.publish("esp32/response", "喇叭擴音器已關閉");
        Serial.println("🔇 喇叭擴音器已關閉");
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
        audioManager.setDebug(enableDebug);
        speakerManager.setDebug(enableDebug);

        String response = "Debug模式: " + String(enableDebug ? "已啟用" : "已停用");
        mqttManager.publish("esp32/response", response.c_str());
        Serial.printf("🔧 設定Debug模式: %s\n", enableDebug ? "啟用" : "停用");
    }
    else if (topic == "esp32/config/volume_threshold")
    {
        float threshold = value.toFloat();
        if (threshold > 0.0 && threshold < 1.0)
        {
            audioManager.setVolumeThreshold(threshold);
            String response = "音量閾值設為: " + String(threshold, 3);
            mqttManager.publish("esp32/response", response.c_str());
            Serial.printf("🔊 音量閾值設為: %.3f\n", threshold);
        }
        else
        {
            mqttManager.publish("esp32/response", "無效的音量閾值 (0.0-1.0)");
        }
    }
    else if (topic == "esp32/config/speaker_volume")
    {
        float volume = value.toFloat();
        if (volume >= 0.0 && volume <= 1.0)
        {
            speakerManager.setVolume(volume);
            String response = "喇叭音量設為: " + String(volume, 2);
            mqttManager.publish("esp32/response", response.c_str());
            Serial.printf("🔊 喇叭音量設為: %.2f\n", volume);
        }
        else
        {
            mqttManager.publish("esp32/response", "無效的喇叭音量 (0.0-1.0)");
        }
    }
    else if (topic == "esp32/config/play_tone")
    {
        // 格式: "frequency,duration" 例如: "1000,500"
        int commaIndex = value.indexOf(',');
        if (commaIndex > 0)
        {
            float freq = value.substring(0, commaIndex).toFloat();
            int dur = value.substring(commaIndex + 1).toInt();

            if (freq > 0 && dur > 0)
            {
                speakerManager.playTone(freq, dur);
                String response = "播放音調: " + String(freq, 1) + "Hz, " + String(dur) + "ms";
                mqttManager.publish("esp32/response", response.c_str());
                Serial.printf("🎵 播放音調: %.1fHz, %dms\n", freq, dur);
            }
        }
    }
    else if (topic == "esp32/config/speaker_gain")
    {
        int gain = value.toInt();
        if (gain >= 0 && gain <= 255)
        {
            speakerManager.setGain(gain);
            String response = "喇叭增益設為: " + String(gain) + "/255";
            mqttManager.publish("esp32/response", response.c_str());
            Serial.printf("🔊 喇叭增益設為: %d/255\n", gain);
        }
        else
        {
            mqttManager.publish("esp32/response", "無效的增益值 (0-255)");
        }
    }
    else
    {
        String response = "未知配置: " + topic;
        mqttManager.publish("esp32/response", response.c_str());
        Serial.printf("❓ 未知配置: %s\n", topic.c_str());
    }
}

// 音訊數據回調函數
void onAudioData(float volume, float *frequencies, int freqCount)
{
    // 發送音量數據到MQTT
    String volumeData = String(volume, 3);
    mqttManager.publish("esp32/audio/volume", volumeData.c_str());

    // 發送主要頻率數據（簡化版）
    if (freqCount > 0)
    {
        String freqData = String(frequencies[0], 1); // 主要頻率
        for (int i = 1; i < min(freqCount, 5); i++)
        {
            freqData += "," + String(frequencies[i], 1);
        }
        mqttManager.publish("esp32/audio/frequencies", freqData.c_str());
    }

    // 語音檢測邏輯 (簡單示例)
    if (volume > 0.3) // 高音量可能是語音
    {
        Serial.printf("🗣️ 檢測到語音活動，音量: %.3f\n", volume);
        mqttManager.publish("esp32/voice/detected", "true");
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

    Serial.println("🚀 ESP32 語音指令系統啟動");
    Serial.println("==========================");

    // 連接WiFi
    Serial.println("📶 連接WiFi...");
    wifiManager.connect();
    if (!wifiManager.isConnected())
    {
        Serial.println("❌ WiFi連接失敗，系統停止");
        return;
    }
    Serial.printf("✅ WiFi已連接，IP: %s\n", wifiManager.getIP().c_str());

    // 初始化音訊系統
    Serial.println("🎤 初始化音訊系統...");
    if (!audioManager.begin())
    {
        Serial.println("❌ 音訊系統初始化失敗");
        return;
    }

    // 初始化喇叭系統
    Serial.println("🔊 初始化喇叭系統...");
    if (!speakerManager.begin())
    {
        Serial.println("❌ 喇叭系統初始化失敗");
        return;
    }

    // 設定音訊回調
    audioManager.setAudioCallback(onAudioData);
    audioManager.setVolumeThreshold(0.1f); // 設定音量閾值

    // 設定喇叭音量
    speakerManager.setVolume(0.3f); // 設定適中音量

    // 設定MQTT回調
    mqttManager.setMessageCallback(onMQTTMessage);
    mqttManager.setConnectionCallback(onMQTTConnect);

    // 初始化MQTT
    mqttManager.begin();
    mqttManager.setAutoReconnect(true, 5000);

    // 連接MQTT
    if (wifiManager.isConnected())
    {
        mqttManager.connect();
    }

    Serial.println("🎧 系統就緒，開始音訊監控...");

    // 自動開始音訊錄製以顯示即時音量
    if (audioManager.startRecording())
    {
        Serial.println("🎙️ 音訊監控已自動啟動");
        Serial.println("💡 音量將持續顯示在序列埠輸出");
    }
    else
    {
        Serial.println("❌ 音訊監控啟動失敗");
    }

    Serial.println("💡 可用指令:");
    Serial.println("   音訊: start_audio, stop_audio, audio_status");
    Serial.println("   喇叭: play_beep, play_alarm, play_melody, speaker_status");
    Serial.println("        speaker_enable, speaker_disable");
    Serial.println("   系統: status, ping, restart");
    Serial.println("🎵 系統就緒，使用 MQTT 指令測試喇叭功能");
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