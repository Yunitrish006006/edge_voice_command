#include "speaker_manager.h"

SpeakerManager::SpeakerManager(bool debug)
    : initialized(false), playing(false), debug_enabled(debug), taskShouldStop(false),
      speakerTaskHandle(nullptr), volume(0.5f), frequency(1000.0f), duration(200), playStartTime(0)
{
    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] SpeakerManager 建構中...");
    }
}

SpeakerManager::~SpeakerManager()
{
    end();
}

bool SpeakerManager::begin()
{
    if (initialized)
    {
        if (debug_enabled)
        {
            Serial.println("[Speaker Debug] SpeakerManager 已初始化");
        }
        return true;
    }

    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] 初始化 I2S 喇叭...");
        Serial.printf("[Speaker Debug] BCLK: GPIO%d, LRC: GPIO%d, DIN: GPIO%d\n",
                      I2S_BCLK_PIN, I2S_WS_PIN, I2S_DATA_PIN);
        Serial.printf("[Speaker Debug] GAIN: GPIO%d, SD: GPIO%d\n",
                      GAIN_PIN, SD_PIN);
        Serial.printf("[Speaker Debug] 採樣率: %d Hz, 位元數: %d\n", SAMPLE_RATE, SAMPLE_BITS);
    }

    // I2S 配置 (輸出模式)
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX), // 傳輸模式
        .sample_rate = SAMPLE_RATE,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_RIGHT_LEFT, // 立體聲
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 4,
        .dma_buf_len = BUFFER_SIZE,
        .use_apll = false,
        .tx_desc_auto_clear = true,
        .fixed_mclk = 0};

    // I2S pin 配置
    i2s_pin_config_t pin_config = {
        .bck_io_num = I2S_BCLK_PIN,
        .ws_io_num = I2S_WS_PIN,
        .data_out_num = I2S_DATA_PIN,
        .data_in_num = I2S_PIN_NO_CHANGE};

    // 安裝 I2S 驅動
    esp_err_t result = i2s_driver_install(I2S_PORT, &i2s_config, 0, NULL);
    if (result != ESP_OK)
    {
        Serial.printf("❌ I2S 喇叭驅動安裝失敗: %s\n", esp_err_to_name(result));
        return false;
    }

    // 設定 I2S pin
    result = i2s_set_pin(I2S_PORT, &pin_config);
    if (result != ESP_OK)
    {
        Serial.printf("❌ I2S 喇叭 pin 設定失敗: %s\n", esp_err_to_name(result));
        i2s_driver_uninstall(I2S_PORT);
        return false;
    }

    // 初始化控制接腳
    pinMode(SD_PIN, OUTPUT);   // SD (Shutdown) 控制
    pinMode(GAIN_PIN, OUTPUT); // GAIN 控制

    // 啟用喇叭 (SD pin 通常是低電位啟用或高電位啟用，這裡假設高電位啟用)
    digitalWrite(SD_PIN, HIGH);

    // 設定預設增益 (PWM 輸出，128 = 50% 增益)
    analogWrite(GAIN_PIN, 128);

    // 清除 I2S 緩衝區
    i2s_zero_dma_buffer(I2S_PORT);

    initialized = true;

    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] ✅ I2S 喇叭初始化成功");
    }

    Serial.println("🔊 喇叭系統已初始化");

    return true;
}

void SpeakerManager::end()
{
    if (!initialized)
        return;

    stopPlaying();

    // 關閉喇叭
    digitalWrite(SD_PIN, LOW);   // 關閉喇叭
    digitalWrite(GAIN_PIN, LOW); // 關閉增益

    i2s_driver_uninstall(I2S_PORT);
    initialized = false;

    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] SpeakerManager 已停止");
    }

    Serial.println("🔇 喇叭系統已停止");
}

bool SpeakerManager::startPlaying()
{
    if (!initialized)
    {
        Serial.println("❌ 喇叭系統未初始化");
        return false;
    }

    if (playing)
    {
        if (debug_enabled)
        {
            Serial.println("[Speaker Debug] 喇叭已在播放中，停止舊任務");
        }
        stopPlaying();
    }

    // 重置控制變數
    taskShouldStop = false;
    playStartTime = millis();

    // 創建喇叭播放任務
    BaseType_t result = xTaskCreatePinnedToCore(
        speakerTask,
        "SpeakerTask",
        8192,
        this,
        2, // 較高優先級
        &speakerTaskHandle,
        1); // 固定在核心1

    if (result != pdPASS)
    {
        Serial.println("❌ 喇叭任務創建失敗");
        return false;
    }

    playing = true;

    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] 開始喇叭播放");
    }

    Serial.println("🔊 開始喇叭播放");

    return true;
}

void SpeakerManager::stopPlaying()
{
    if (!playing)
        return;

    // 通知任務停止
    taskShouldStop = true;
    playing = false;

    // 等待任務自然結束
    if (speakerTaskHandle != nullptr)
    {
        // 等待最多500ms讓任務自己結束
        for (int i = 0; i < 50 && speakerTaskHandle != nullptr; i++)
        {
            vTaskDelay(pdMS_TO_TICKS(10));
        }

        // 如果任務還沒結束，強制刪除
        if (speakerTaskHandle != nullptr)
        {
            vTaskDelete(speakerTaskHandle);
            speakerTaskHandle = nullptr;
        }
    }

    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] 停止喇叭播放");
    }

    Serial.println("🔇 喇叭播放已停止");
}

void SpeakerManager::speakerTask(void *parameter)
{
    SpeakerManager *speakerManager = static_cast<SpeakerManager *>(parameter);
    int16_t audioBuffer[BUFFER_SIZE * 2]; // 立體聲需要雙倍緩衝區
    size_t bytesWritten = 0;

    const TickType_t xDelay = pdMS_TO_TICKS(10); // 10ms 延遲

    while (speakerManager->playing && !speakerManager->taskShouldStop)
    {
        // 檢查播放時間限制
        if (speakerManager->duration > 0)
        {
            unsigned long elapsed = millis() - speakerManager->playStartTime;
            if (elapsed >= (unsigned long)speakerManager->duration)
            {
                if (speakerManager->debug_enabled)
                {
                    Serial.println("[Speaker Debug] 播放時間到，任務自動結束");
                }
                break;
            }
        }

        // 生成音訊數據
        speakerManager->generateTone(audioBuffer, BUFFER_SIZE,
                                     speakerManager->frequency,
                                     speakerManager->volume);

        // 寫入 I2S 數據
        esp_err_t result = i2s_write(I2S_PORT, audioBuffer,
                                     sizeof(audioBuffer),
                                     &bytesWritten, pdMS_TO_TICKS(100)); // 100ms 超時

        if (result != ESP_OK)
        {
            Serial.printf("❌ I2S 寫入失敗: %s\n", esp_err_to_name(result));
            break;
        }

        vTaskDelay(xDelay);
    }

    // 任務結束，清理狀態
    speakerManager->playing = false;
    speakerManager->speakerTaskHandle = nullptr;

    if (speakerManager->debug_enabled)
    {
        Serial.println("[Speaker Debug] 喇叭任務自然結束");
    }

    vTaskDelete(NULL); // 自己刪除自己
}

void SpeakerManager::generateTone(int16_t *buffer, size_t samples, float freq, float vol)
{
    static float phase = 0.0f;
    float phaseIncrement = 2.0f * M_PI * freq / SAMPLE_RATE;

    for (size_t i = 0; i < samples; i++)
    {
        // 生成正弦波
        float sampleValue = sin(phase) * vol * 32767.0f * 0.3f; // 限制音量避免削波
        int16_t sample = (int16_t)sampleValue;

        // 立體聲輸出 (左右聲道相同)
        buffer[i * 2] = sample;     // 左聲道
        buffer[i * 2 + 1] = sample; // 右聲道

        phase += phaseIncrement;
        if (phase >= 2.0f * M_PI)
        {
            phase -= 2.0f * M_PI;
        }
    }
}

void SpeakerManager::generateBeep(int16_t *buffer, size_t samples)
{
    generateTone(buffer, samples, 1000.0f, volume); // 1kHz 嗶聲
}

void SpeakerManager::generateAlarm(int16_t *buffer, size_t samples)
{
    static float alarmPhase = 0.0f;
    float alarmFreq = 800.0f + 400.0f * sin(alarmPhase); // 800-1200Hz 變化
    generateTone(buffer, samples, alarmFreq, volume);
    alarmPhase += 0.1f;
    if (alarmPhase >= 2.0f * M_PI)
    {
        alarmPhase = 0.0f;
    }
}

bool SpeakerManager::playTone(float freq, int duration_ms)
{
    if (!initialized)
        return false;

    frequency = freq;
    duration = duration_ms;

    if (debug_enabled)
    {
        Serial.printf("[Speaker Debug] 播放音調: %.1f Hz, %d ms\n", freq, duration_ms);
    }

    if (!startPlaying())
        return false;

    // 等待播放完成 (不使用delay，避免阻塞)
    if (duration_ms > 0)
    {
        unsigned long startTime = millis();
        while (playing && (millis() - startTime) < (unsigned long)duration_ms + 100) // 多等100ms確保完成
        {
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }

    return true;
}

bool SpeakerManager::playBeep(int duration_ms)
{
    return playTone(1000.0f, duration_ms);
}

bool SpeakerManager::playAlarm(int duration_ms)
{
    if (!initialized)
        return false;

    duration = duration_ms;

    if (debug_enabled)
    {
        Serial.printf("[Speaker Debug] 播放警報: %d ms\n", duration_ms);
    }

    if (!startPlaying())
        return false;

    delay(duration_ms);
    stopPlaying();

    return true;
}

bool SpeakerManager::playMelody(float *frequencies, int *durations, int noteCount)
{
    if (!initialized)
        return false;

    if (debug_enabled)
    {
        Serial.printf("[Speaker Debug] 播放旋律: %d 個音符\n", noteCount);
    }

    for (int i = 0; i < noteCount; i++)
    {
        if (frequencies[i] > 0)
        {
            playTone(frequencies[i], durations[i]);
        }
        else
        {
            delay(durations[i]); // 休止符
        }
        delay(50); // 音符間隔
    }

    return true;
}

// Getter/Setter 方法
bool SpeakerManager::isInitialized() { return initialized; }
bool SpeakerManager::isPlaying() { return playing; }
float SpeakerManager::getVolume() { return volume; }

void SpeakerManager::setVolume(float vol)
{
    if (vol < 0.0f)
        vol = 0.0f;
    if (vol > 1.0f)
        vol = 1.0f;
    volume = vol;

    if (debug_enabled)
    {
        Serial.printf("[Speaker Debug] 音量設為: %.2f\n", volume);
    }
}

void SpeakerManager::setDebug(bool enable)
{
    debug_enabled = enable;
    if (debug_enabled)
    {
        Serial.println("[Speaker Debug] 喇叭除錯模式已啟用");
    }
}

void SpeakerManager::enableAmplifier(bool enable)
{
    digitalWrite(SD_PIN, enable ? HIGH : LOW);
    if (debug_enabled)
    {
        Serial.printf("[Speaker Debug] 擴音器 %s\n", enable ? "啟用" : "關閉");
    }
}

void SpeakerManager::setHardwareGain(int gain_level)
{
    if (gain_level < 0)
        gain_level = 0;
    if (gain_level > 255)
        gain_level = 255;

    analogWrite(GAIN_PIN, gain_level);

    if (debug_enabled)
    {
        Serial.printf("[Speaker Debug] 硬體增益設為: %d/255\n", gain_level);
    }
}

void SpeakerManager::setGain(int gain_level)
{
    setHardwareGain(gain_level);
}

void SpeakerManager::printStatus()
{
    Serial.println("🔊 喇叭系統狀態:");
    Serial.printf("   初始化: %s\n", initialized ? "是" : "否");
    Serial.printf("   播放中: %s\n", playing ? "是" : "否");
    Serial.printf("   音量: %.2f\n", volume);
    Serial.printf("   頻率: %.1f Hz\n", frequency);
    Serial.printf("   BCLK: GPIO%d, LRC: GPIO%d, DIN: GPIO%d\n",
                  I2S_BCLK_PIN, I2S_WS_PIN, I2S_DATA_PIN);
    Serial.printf("   GAIN: GPIO%d, SD: GPIO%d\n", GAIN_PIN, SD_PIN);
    Serial.printf("   擴音器狀態: %s\n", digitalRead(SD_PIN) ? "啟用" : "關閉");
}
