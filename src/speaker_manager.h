#ifndef SPEAKER_MANAGER_H
#define SPEAKER_MANAGER_H

#include <Arduino.h>
#include <driver/i2s.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <math.h>

class SpeakerManager
{
private:
    // I2S 配置
    static const i2s_port_t I2S_PORT = I2S_NUM_1; // 使用 I2S_NUM_1 避免與麥克風衝突
    static const int SAMPLE_RATE = 16000;
    static const int SAMPLE_BITS = 16;
    static const int BUFFER_SIZE = 1024;

    // GPIO 配置 (喇叭輸出)
    static const int I2S_BCLK_PIN = 14; // 位元時脈 (BCLK)
    static const int I2S_WS_PIN = 15;   // 字時脈 (LRC/LRCLK)
    static const int I2S_DATA_PIN = 13; // 數據線 (DIN)
    static const int GAIN_PIN = 12;     // 音量增益控制 (GAIN)
    static const int SD_PIN = 11;       // 啟用/關閉控制 (SD - Shutdown)

    // 狀態控制
    bool initialized;
    bool playing;
    bool debug_enabled;
    TaskHandle_t speakerTaskHandle;

    // 音訊參數
    float volume;
    float frequency;
    int duration;

    // 音訊生成
    void generateTone(int16_t *buffer, size_t samples, float freq, float vol);
    void generateBeep(int16_t *buffer, size_t samples);
    void generateAlarm(int16_t *buffer, size_t samples);

public:
    SpeakerManager(bool debug = false);
    ~SpeakerManager();

    // 基本控制
    bool begin();
    void end();
    bool isInitialized();

    // 播放控制
    bool startPlaying();
    void stopPlaying();
    bool isPlaying();

    // 音量控制
    void setVolume(float vol); // 0.0 到 1.0
    float getVolume();
    void setGain(int gain_level); // 硬體增益控制 0-255

    // 硬體控制
    void enableAmplifier(bool enable);
    void setHardwareGain(int gain_level); // 0-255

    // 播放功能
    bool playTone(float frequency, int duration_ms);
    bool playBeep(int duration_ms = 200);
    bool playAlarm(int duration_ms = 1000);
    bool playMelody(float *frequencies, int *durations, int noteCount);

    // Debug 控制
    void setDebug(bool enable);

    // 靜態任務函數
    static void speakerTask(void *parameter);

    // 狀態資訊
    void printStatus();
};

#endif // SPEAKER_MANAGER_H
