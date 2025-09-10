#ifndef AUDIO_MANAGER_H
#define AUDIO_MANAGER_H

#include <Arduino.h>
#include <driver/i2s.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <ArduinoFFT.h>

class AudioManager
{
private:
    // I2S 配置
    static const i2s_port_t I2S_PORT = I2S_NUM_0;
    static const int SAMPLE_RATE = 16000;
    static const int SAMPLE_BITS = 16;
    static const int BUFFER_SIZE = 1024;

    // GPIO 配置
    static const int I2S_BCLK_PIN = 1;  // 位元時脈
    static const int I2S_WS_PIN = 2;    // 字時脈 (LRCLK)
    static const int I2S_DATA_PIN = 42; // 數據線

    // FFT 分析
    static const int FFT_SIZE = 512;
    double vReal[FFT_SIZE];
    double vImag[FFT_SIZE];
    ArduinoFFT<double> FFT;

    // 狀態控制
    bool initialized;
    bool recording;
    bool debug_enabled;
    TaskHandle_t audioTaskHandle;

    // 音量檢測
    float currentVolume;
    float volumeThreshold;

    // 回調函數
    typedef std::function<void(float volume, float *frequencies, int freqCount)> AudioCallback;
    AudioCallback audioCallback;

public:
    AudioManager(bool debug = false);
    ~AudioManager();

    // 基本控制
    bool begin();
    void end();
    bool isInitialized();

    // 錄音控制
    bool startRecording();
    void stopRecording();
    bool isRecording();

    // 音量控制
    void setVolumeThreshold(float threshold);
    float getCurrentVolume();
    float getVolumeThreshold();

    // 回調設定
    void setAudioCallback(AudioCallback callback);

    // Debug 控制
    void setDebug(bool enable);

    // 音訊分析
    void processAudioData(int16_t *audioBuffer, size_t bufferSize);
    float calculateVolume(int16_t *audioBuffer, size_t bufferSize);
    void performFFT(int16_t *audioBuffer, size_t bufferSize, float *frequencies, int freqCount);

    // 靜態任務函數
    static void audioTask(void *parameter);

    // 狀態資訊
    void printStatus();
};

#endif // AUDIO_MANAGER_H
