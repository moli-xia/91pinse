import tkinter as tk
from tkinter import messagebox
import yt_dlp
import threading
import re
import requests
import os
import subprocess
import sys

def get_download_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_PATH = get_download_path()

def open_download_folder():
    try:
        if sys.platform == "win32":
            os.startfile(DOWNLOAD_PATH)
        elif sys.platform == "darwin":
            subprocess.run(["open", DOWNLOAD_PATH])
        else:
            subprocess.run(["xdg-open", DOWNLOAD_PATH])
    except Exception as e:
        messagebox.showerror("错误", f"无法打开下载文件夹。\n{e}")

def find_video_url(page_url):
    try:
        status_label.config(text="第1/3步: 正在获取主页面...")
        main_page_response = requests.get(page_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15)
        main_page_response.raise_for_status()

        status_label.config(text="第2/3步: 正在查找播放器...")
        iframe_match = re.search(r'src="(https?://fplayer\.cc/embed/[^"]+)"', main_page_response.text)
        
        if not iframe_match:
            iframe_match = re.search(r'src=(https?://fplayer\.cc/embed/[^\s>]+)', main_page_response.text)

        if not iframe_match:
            status_label.config(text="错误: 找不到视频播放器。")
            return None
        
        iframe_url = iframe_match.group(1)

        status_label.config(text="第3/3步: 正在提取视频链接...")
        iframe_response = requests.get(iframe_url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': page_url}, timeout=15)
        iframe_response.raise_for_status()

        video_match = re.search(r'source:\s*\'(https?://[^\']+\.mp4)\'', iframe_response.text)
        if video_match:
            return video_match.group(1)
        
        video_match_fallback = re.search(r'(https?://[^\'"\s]+\.mp4)', iframe_response.text)
        if video_match_fallback:
            return video_match_fallback.group(1)

        status_label.config(text="错误: 找到播放器但无法提取链接。")
        return None

    except requests.exceptions.RequestException as e:
        status_label.config(text=f"网络错误: {e}")
        return None
    except Exception as e:
        status_label.config(text=f"发生未知错误: {e}")
        return None

def start_download():
    page_url = url_entry.get()
    if not page_url:
        messagebox.showerror("错误", "请输入网页地址")
        return

    download_button.config(state=tk.DISABLED)
    open_folder_button.config(state=tk.DISABLED)
    status_label.config(text="任务开始...")
    
    threading.Thread(target=download_video, args=(page_url,), daemon=True).start()

def download_video(page_url):
    video_url = find_video_url(page_url)

    if not video_url:
        status_label.config(text="无法找到视频链接，请尝试其他地址。")
        download_button.config(state=tk.NORMAL)
        open_folder_button.config(state=tk.NORMAL)
        return

    status_label.config(text="已找到链接！准备开始下载...")

    try:
        ydl_opts = {
            'progress_hooks': [hook],
            'paths': {'home': DOWNLOAD_PATH},
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s')
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        status_label.config(text="下载完成！")
        messagebox.showinfo("成功", f"视频已成功下载到:\n{DOWNLOAD_PATH}")
    except Exception as e:
        status_label.config(text=f"下载出错: {e}")
        messagebox.showerror("错误", f"下载视频失败。\n{e}")
    finally:
        download_button.config(state=tk.NORMAL)
        open_folder_button.config(state=tk.NORMAL)

def hook(d):
    if d['status'] == 'downloading':
        percent_str = d['_percent_str'].strip()
        speed_str = d.get('_speed_str', '').strip()
        eta_str = d.get('_eta_str', '').strip()
        status_label.config(text=f"正在下载: {percent_str} (速度: {speed_str}) 剩余时间: {eta_str}")
    elif d['status'] == 'finished':
        status_label.config(text="下载完成，正在处理...")

# --- GUI Setup ---
root = tk.Tk()
root.title("91pinse下载器")

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(padx=10, pady=10)

url_label = tk.Label(frame, text="网页地址:")
url_label.pack(pady=(0, 5))

url_entry = tk.Entry(frame, width=60)
url_entry.pack(pady=5)

button_frame = tk.Frame(frame)
button_frame.pack(pady=10)

download_button = tk.Button(button_frame, text="解析并下载", command=start_download)
download_button.pack(side=tk.LEFT, padx=5)

open_folder_button = tk.Button(button_frame, text="打开下载目录", command=open_download_folder)
open_folder_button.pack(side=tk.LEFT, padx=5)

status_label = tk.Label(frame, text="请输入网页地址，然后点击下载。", wraplength=400, justify=tk.LEFT)
status_label.pack(pady=5)

root.mainloop()