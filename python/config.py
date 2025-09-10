#!/usr/bin/env python3
"""
MQTT 配置管理器
"""

import configparser
import os

class MQTTConfig:
    def __init__(self, config_file="config.ini"):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """載入配置文件"""
        if os.path.exists(self.config_file):
            self.config.read(self.config_file, encoding='utf-8')
        else:
            self.create_default_config()
    
    def create_default_config(self):
        """創建預設配置"""
        self.config['broker'] = {
            'custom_host': '192.168.1.121',
            'custom_port': '1883',
            'external_host': 'broker.hivemq.com',
            'external_port': '1883',
            'use_broker': 'custom'
        }
        
        self.config['topics'] = {
            'voice_command': 'esp32/voice_command',
            'device_status': 'esp32/status',
            'sensor_data': 'esp32/sensors',
            'control': 'esp32/control'
        }
        
        self.config['client'] = {
            'client_id_prefix': 'ESP32_Voice_',
            'keep_alive': '60',
            'qos': '1'
        }
        
        self.config['gui'] = {
            'window_width': '900',
            'window_height': '650',
            'auto_scroll': 'true',
            'max_log_lines': '1000'
        }
        
        self.save_config()
    
    def save_config(self):
        """儲存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)
    
    def get_broker_info(self):
        """取得 broker 資訊"""
        use_broker = self.config.get('broker', 'use_broker', fallback='custom')
        
        if use_broker == 'custom':
            host = self.config.get('broker', 'custom_host', fallback='localhost')
            port = self.config.getint('broker', 'custom_port', fallback=1883)
        else:
            host = self.config.get('broker', 'external_host', fallback='broker.hivemq.com')
            port = self.config.getint('broker', 'external_port', fallback=1883)
        
        return host, port
    
    def get_topics(self):
        """取得主題列表"""
        return {
            'voice_command': self.config.get('topics', 'voice_command', fallback='esp32/voice_command'),
            'device_status': self.config.get('topics', 'device_status', fallback='esp32/status'),
            'sensor_data': self.config.get('topics', 'sensor_data', fallback='esp32/sensors'),
            'control': self.config.get('topics', 'control', fallback='esp32/control')
        }
    
    def get_client_config(self):
        """取得客戶端配置"""
        return {
            'client_id_prefix': self.config.get('client', 'client_id_prefix', fallback='ESP32_Voice_'),
            'keep_alive': self.config.getint('client', 'keep_alive', fallback=60),
            'qos': self.config.getint('client', 'qos', fallback=1)
        }
    
    def get_gui_config(self):
        """取得 GUI 配置"""
        return {
            'window_width': self.config.getint('gui', 'window_width', fallback=900),
            'window_height': self.config.getint('gui', 'window_height', fallback=650),
            'auto_scroll': self.config.getboolean('gui', 'auto_scroll', fallback=True),
            'max_log_lines': self.config.getint('gui', 'max_log_lines', fallback=1000)
        }
    
    def set_broker_mode(self, mode):
        """設定 broker 模式 (custom 或 external)"""
        if mode not in ['custom', 'external']:
            raise ValueError("模式必須是 'custom' 或 'external'")
        self.config.set('broker', 'use_broker', mode)
        self.save_config()

if __name__ == "__main__":
    # 測試配置管理器
    config = MQTTConfig()
    
    print("Broker 資訊:", config.get_broker_info())
    print("主題列表:", config.get_topics())
    print("客戶端配置:", config.get_client_config())
    print("GUI 配置:", config.get_gui_config())
