#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
視窗大小配置助手
讓用戶可以快速調整 GUI 視窗大小設定
"""

import tkinter as tk
from tkinter import ttk, messagebox
from config import MQTTConfig

class WindowSizeConfig:
    """視窗大小配置界面"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("🖥️ 視窗大小配置")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # 載入配置
        self.config = MQTTConfig()
        self.current_config = self.config.get_gui_config()
        
        self.setup_ui()
        
        # 視窗置中
        self.center_window()
    
    def center_window(self):
        """將視窗置中顯示"""
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.root.winfo_screenheight() // 2) - (400 // 2)
        self.root.geometry(f"500x400+{x}+{y}")
    
    def setup_ui(self):
        """建立使用者介面"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 標題
        title_label = ttk.Label(main_frame, text="🖥️ GUI 視窗大小配置", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # 當前設定顯示
        current_frame = ttk.LabelFrame(main_frame, text="當前設定", padding="10")
        current_frame.pack(fill=tk.X, pady=(0, 20))
        
        current_width = self.current_config['window_width']
        current_height = self.current_config['window_height']
        
        current_info = ttk.Label(current_frame, 
                                text=f"目前視窗大小: {current_width} x {current_height} 像素",
                                font=("Arial", 12))
        current_info.pack()
        
        # 預設大小選項
        presets_frame = ttk.LabelFrame(main_frame, text="預設大小選項", padding="10")
        presets_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.size_var = tk.StringVar(value="custom")
        
        presets = [
            ("小螢幕 (900x600)", "900x600", "適合筆電和小螢幕"),
            ("中等螢幕 (1200x800)", "1200x800", "適合一般桌機螢幕"),
            ("大螢幕 (1400x900)", "1400x900", "適合大螢幕顯示器"),
            ("超寬螢幕 (1600x1000)", "1600x1000", "適合超寬或多螢幕"),
        ]
        
        for name, size, desc in presets:
            frame = ttk.Frame(presets_frame)
            frame.pack(fill=tk.X, pady=2)
            
            radio = ttk.Radiobutton(frame, text=name, variable=self.size_var, 
                                   value=size, command=self.on_preset_selected)
            radio.pack(side=tk.LEFT)
            
            desc_label = ttk.Label(frame, text=f"- {desc}", 
                                  foreground="gray", font=("Arial", 9))
            desc_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # 自訂大小
        custom_frame = ttk.LabelFrame(main_frame, text="自訂大小", padding="10")
        custom_frame.pack(fill=tk.X, pady=(0, 20))
        
        # 自訂選項
        custom_radio_frame = ttk.Frame(custom_frame)
        custom_radio_frame.pack(fill=tk.X, pady=(0, 10))
        
        custom_radio = ttk.Radiobutton(custom_radio_frame, text="自訂大小", 
                                      variable=self.size_var, value="custom",
                                      command=self.on_custom_selected)
        custom_radio.pack(side=tk.LEFT)
        
        # 寬度設定
        width_frame = ttk.Frame(custom_frame)
        width_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(width_frame, text="寬度:").pack(side=tk.LEFT)
        self.width_var = tk.StringVar(value=str(current_width))
        self.width_entry = ttk.Entry(width_frame, textvariable=self.width_var, 
                                    width=10)
        self.width_entry.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(width_frame, text="像素").pack(side=tk.LEFT)
        
        # 高度設定
        height_frame = ttk.Frame(custom_frame)
        height_frame.pack(fill=tk.X)
        
        ttk.Label(height_frame, text="高度:").pack(side=tk.LEFT)
        self.height_var = tk.StringVar(value=str(current_height))
        self.height_entry = ttk.Entry(height_frame, textvariable=self.height_var, 
                                     width=10)
        self.height_entry.pack(side=tk.LEFT, padx=(10, 5))
        ttk.Label(height_frame, text="像素").pack(side=tk.LEFT)
        
        # 預覽和說明
        preview_frame = ttk.LabelFrame(main_frame, text="預覽", padding="10")
        preview_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.preview_label = ttk.Label(preview_frame, text="", 
                                      font=("Arial", 10), foreground="blue")
        self.preview_label.pack()
        
        self.update_preview()
        
        # 按鈕區域
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        # 測試按鈕
        test_btn = ttk.Button(button_frame, text="🔍 測試視窗大小", 
                             command=self.test_window_size)
        test_btn.pack(side=tk.LEFT)
        
        # 重置按鈕
        reset_btn = ttk.Button(button_frame, text="🔄 重置為預設", 
                              command=self.reset_to_default)
        reset_btn.pack(side=tk.LEFT, padx=(10, 0))
        
        # 應用和取消按鈕
        apply_btn = ttk.Button(button_frame, text="✅ 應用設定", 
                              command=self.apply_settings)
        apply_btn.pack(side=tk.RIGHT)
        
        cancel_btn = ttk.Button(button_frame, text="❌ 取消", 
                               command=self.root.destroy)
        cancel_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        # 綁定事件
        self.width_var.trace('w', self.on_custom_change)
        self.height_var.trace('w', self.on_custom_change)
        
        # 檢查當前設定是否符合預設
        self.check_current_preset()
    
    def check_current_preset(self):
        """檢查當前設定是否符合某個預設"""
        current_size = f"{self.current_config['window_width']}x{self.current_config['window_height']}"
        presets = ["900x600", "1200x800", "1400x900", "1600x1000"]
        
        if current_size in presets:
            self.size_var.set(current_size)
        else:
            self.size_var.set("custom")
    
    def on_preset_selected(self):
        """選擇預設大小時的處理"""
        selected = self.size_var.get()
        if selected != "custom":
            width, height = selected.split('x')
            self.width_var.set(width)
            self.height_var.set(height)
            self.update_preview()
    
    def on_custom_selected(self):
        """選擇自訂大小時的處理"""
        self.update_preview()
    
    def on_custom_change(self, *args):
        """自訂數值改變時的處理"""
        if self.size_var.get() == "custom":
            self.update_preview()
    
    def update_preview(self):
        """更新預覽顯示"""
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            
            # 檢查合理範圍
            if width < 400 or height < 300:
                self.preview_label.config(text="⚠️ 視窗太小，可能影響使用體驗", 
                                         foreground="orange")
            elif width > 2000 or height > 1200:
                self.preview_label.config(text="⚠️ 視窗很大，確保螢幕能容納", 
                                         foreground="orange")
            else:
                # 計算比例
                ratio = width / height
                if ratio > 2.0:
                    aspect = "超寬比例"
                elif ratio > 1.5:
                    aspect = "寬螢幕比例"
                elif ratio > 1.2:
                    aspect = "標準比例"
                else:
                    aspect = "接近正方形"
                
                self.preview_label.config(text=f"✅ 視窗大小: {width}x{height} ({aspect})", 
                                         foreground="blue")
        except ValueError:
            self.preview_label.config(text="❌ 請輸入有效的數字", 
                                     foreground="red")
    
    def test_window_size(self):
        """測試視窗大小"""
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            
            if width < 200 or height < 150:
                messagebox.showwarning("大小錯誤", "視窗大小過小")
                return
            
            if width > 3000 or height > 2000:
                messagebox.showwarning("大小錯誤", "視窗大小過大")
                return
            
            # 創建測試視窗
            test_window = tk.Toplevel(self.root)
            test_window.title("🔍 視窗大小測試")
            test_window.geometry(f"{width}x{height}")
            test_window.resizable(True, True)
            
            # 測試內容
            test_frame = ttk.Frame(test_window, padding="20")
            test_frame.pack(fill=tk.BOTH, expand=True)
            
            ttk.Label(test_frame, text="📏 視窗大小測試", 
                     font=("Arial", 16, "bold")).pack(pady=(0, 10))
            
            size_label = ttk.Label(test_frame, 
                                  text=f"目前大小: {width} x {height} 像素",
                                  font=("Arial", 12))
            size_label.pack(pady=(0, 10))
            
            ttk.Label(test_frame, 
                     text="這是測試視窗，請檢查大小是否合適。\n如果滿意，請關閉此視窗並應用設定。",
                     justify=tk.CENTER).pack(pady=(0, 20))
            
            ttk.Button(test_frame, text="關閉測試視窗", 
                      command=test_window.destroy).pack()
            
            # 視窗置中
            test_window.update_idletasks()
            x = (test_window.winfo_screenwidth() // 2) - (width // 2)
            y = (test_window.winfo_screenheight() // 2) - (height // 2)
            test_window.geometry(f"{width}x{height}+{x}+{y}")
            
        except ValueError:
            messagebox.showerror("輸入錯誤", "請輸入有效的寬度和高度數值")
    
    def reset_to_default(self):
        """重置為預設值"""
        result = messagebox.askyesno("確認重置", "確定要重置為預設大小 (1200x800) 嗎？")
        if result:
            self.width_var.set("1200")
            self.height_var.set("800")
            self.size_var.set("1200x800")
            self.update_preview()
    
    def apply_settings(self):
        """應用設定"""
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
            
            # 驗證數值
            if width < 400 or height < 300:
                messagebox.showerror("大小錯誤", "視窗大小過小，最小為 400x300")
                return
            
            if width > 3000 or height > 2000:
                messagebox.showerror("大小錯誤", "視窗大小過大，最大為 3000x2000")
                return
            
            # 更新配置
            self.config.config.set('gui', 'window_width', str(width))
            self.config.config.set('gui', 'window_height', str(height))
            self.config.save_config()
            
            messagebox.showinfo("設定成功", 
                               f"視窗大小已更新為 {width}x{height}\n重新啟動應用程式後生效")
            
            self.root.destroy()
            
        except ValueError:
            messagebox.showerror("輸入錯誤", "請輸入有效的寬度和高度數值")
    
    def run(self):
        """執行配置程式"""
        self.root.mainloop()

def main():
    """主程式"""
    print("🖥️ 啟動視窗大小配置工具")
    app = WindowSizeConfig()
    app.run()

if __name__ == "__main__":
    main()
