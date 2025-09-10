#include "audio_manager.h"

AudioManager::AudioManager(bool debug)
    : initialized(false), recording(false), debug_enabled(debug),
      audioTaskHandle(nullptr), currentVolume(0.0f), volumeThreshold(0.1f),
      FFT(vReal, vImag, FFT_SIZE, SAMPLE_RATE)
{
    if (debug_enabled)
    {
        Serial.println("[Audio Debug] AudioManager 建構中...");
    }
}

AudioManager::~AudioManager()
{
    end();
}

bool AudioManager::begin()
{
    if (initialized)
    {
        if (debug_enabled)
        {
            Serial.println("[Audio Debug] AudioManager 已初始化");
        }
        return true;
    }

    if (debug_enabled)
    {
        Serial.println("[Audio Debug] 初始化 I2S 麥克風...");
        Serial.printf("[Audio Debug] BCLK: GPIO%d, WS: GPIO%d, DATA: GPIO%d\n",
                      I2S_BCLK_PIN, I2S_WS_PIN, I2S_DATA_PIN);
        Serial.printf("[Audio Debug] 採樣率: %d Hz, 位元數: %d\n", SAMPLE_RATE, SAMPLE_BITS);
    }

    // I2S 配置
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = BUFFER_SIZE,
        .use_apll = false,
        .tx_desc_auto_clear = false,
        .fixed_mclk = 0};

    // I2S pin 配置
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_BCLK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num = I2S_DATA_PIN};

    // 安裝 I2S 驅動
    esp_err_t result = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    if (result != ESP_OK)
    {
        Serial.printf("❌ I2S 驅動安裝失敗: %s\n", esp_err_to_name(result));
        return false;
    }

    // 設定 I2S pin
    result = i2s_set_pin(I2S_PORT, &pin_config);
    if (result != ESP_OK)
    {
        Serial.printf("❌ I2S pin 設定失敗: %s\n", esp_err_to_name(result));
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }

    // 清除 I2S 緩衝區
    i2s_zero_dma_buffer(I2S_PORT);

    initialized = true;

    if (debug_enabled)
    {
        Serial.println("[Audio Debug] ✅ I2S 麥克風初始化成功");
    }

    Serial.println("🎤 音訊系統已初始化");

    return true;
}

void AudioManager::end()
{
    if (!initialized)
        return;

    stopRecording();
    i2s_driver_uninstall(I2S_PORT);
    initialized = false;

    if (debug_enabled)
    {
        Serial.println("[Audio Debug] AudioManager 已停止");
    }

    Serial.println("🔇 音訊系統已停止");
}

bool AudioManager::startRecording()
{
    if (!initialized)
    {
        Serial.println("❌ 音訊系統未初始化");
        return false;
    }

    if (recording)
    {
        if (debug_enabled)
        {
            Serial.println("[Audio Debug] 錄音已在進行中");
        }
        return true;
    }

    // 創建音訊處理任務
    BaseType_t result = xTaskCreatePinnedToCore(
        audioTask,
        "AudioTask",
        8192,
        this,
        1,
        &audioTaskHandle,
        0);

    if (result != pdPASS)
    {
        Serial.println("❌ 音訊任務創建失敗");
        return false;
    }

    recording = true;

    if (debug_enabled)
    {
        Serial.println("[Audio Debug] 開始錄音和分析");
    }

    Serial.println("🎙️ 開始音訊錄製");

    return true;
}

void AudioManager::stopRecording()
{
    if (!recording)
        return;

    recording = false;

    if (audioTaskHandle != nullptr)
    {
        vTaskDelete(audioTaskHandle);
        audioTaskHandle = nullptr;
    }

    if (debug_enabled)
    {
        Serial.println("[Audio Debug] 停止錄音");
    }

    Serial.println("⏹️ 音訊錄製已停止");
}

void AudioManager::audioTask(void *parameter)
{
    AudioManager *audioManager = static_cast<AudioManager *>(parameter);
    int16_t audioBuffer[BUFFER_SIZE];
    size_t bytesRead = 0;

    const TickType_t xDelay = pdMS_TO_TICKS(10); // 10ms 延遲

    while (audioManager->recording)
    {
        // 讀取 I2S 數據
        esp_err_t result = i2s_read(I2S_PORT, audioBuffer, sizeof(audioBuffer), &bytesRead, portMAX_DELAY);

        if (result == ESP_OK && bytesRead > 0)
        {
            size_t samplesRead = bytesRead / sizeof(int16_t);
            audioManager->processAudioData(audioBuffer, samplesRead);
        }

        vTaskDelay(xDelay);
    }

    vTaskDelete(NULL);
}

void AudioManager::processAudioData(int16_t *audioBuffer, size_t bufferSize)
{
    // 計算音量
    currentVolume = calculateVolume(audioBuffer, bufferSize);

    // 如果有設定回調函數，執行頻率分析
    if (audioCallback && currentVolume > volumeThreshold)
    {
        float frequencies[10]; // 前10個主要頻率
        performFFT(audioBuffer, bufferSize, frequencies, 10);
        audioCallback(currentVolume, frequencies, 10);
    }

    // Debug 輸出
    if (debug_enabled && currentVolume > volumeThreshold)
    {
        Serial.printf("[Audio Debug] 音量: %.3f (閾值: %.3f)\n", currentVolume, volumeThreshold);
    }
}

float AudioManager::calculateVolume(int16_t *audioBuffer, size_t bufferSize)
{
    float sum = 0.0f;

    for (size_t i = 0; i < bufferSize; i++)
    {
        float sample = audioBuffer[i] / 32768.0f; // 正規化到 -1.0 ~ 1.0
        sum += sample * sample;
    }

    return sqrt(sum / bufferSize);
}

void AudioManager::performFFT(int16_t *audioBuffer, size_t bufferSize, float *frequencies, int freqCount)
{
    // 限制FFT大小
    size_t fftSize = min(bufferSize, (size_t)FFT_SIZE);

    // 準備FFT數據
    for (size_t i = 0; i < fftSize; i++)
    {
        vReal[i] = audioBuffer[i];
        vImag[i] = 0.0;
    }

    // 執行FFT
    FFT.windowing(vReal, fftSize, FFT_WIN_TYP_HAMMING, FFT_FORWARD);
    FFT.compute(vReal, vImag, fftSize, FFT_FORWARD);
    FFT.complexToMagnitude(vReal, vImag, fftSize);

    // 提取主要頻率
    for (int i = 0; i < freqCount && i < fftSize / 2; i++)
    {
        frequencies[i] = vReal[i];
    }
}

// Getter/Setter 方法
bool AudioManager::isInitialized() { return initialized; }
bool AudioManager::isRecording() { return recording; }
float AudioManager::getCurrentVolume() { return currentVolume; }
float AudioManager::getVolumeThreshold() { return volumeThreshold; }

void AudioManager::setVolumeThreshold(float threshold)
{
    volumeThreshold = threshold;
    if (debug_enabled)
    {
        Serial.printf("[Audio Debug] 音量閾值設為: %.3f\n", threshold);
    }
}

void AudioManager::setAudioCallback(AudioCallback callback)
{
    audioCallback = callback;
    if (debug_enabled)
    {
        Serial.println("[Audio Debug] 音訊回調函數已設定");
    }
}

void AudioManager::setDebug(bool enable)
{
    debug_enabled = enable;
    if (debug_enabled)
    {
        Serial.println("[Audio Debug] 音訊除錯模式已啟用");
    }
}

void AudioManager::printStatus()
{
    Serial.println("🎤 音訊系統狀態:");
    Serial.printf("   初始化: %s\n", initialized ? "是" : "否");
    Serial.printf("   錄音中: %s\n", recording ? "是" : "否");
    Serial.printf("   當前音量: %.3f\n", currentVolume);
    Serial.printf("   音量閾值: %.3f\n", volumeThreshold);
    Serial.printf("   BCLK: GPIO%d, WS: GPIO%d, DATA: GPIO%d\n",
                  I2S_BCLK_PIN, I2S_WS_PIN, I2S_DATA_PIN);
}
