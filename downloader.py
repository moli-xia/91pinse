import tkinter as tk
from tkinter import messagebox
import yt_dlp
import threading
import re
import requests
import os
import subprocess
import sys
from urllib.parse import urljoin, urlparse

def get_download_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_PATH = get_download_path()

def set_status(text):
    try:
        status_label.after(0, lambda: status_label.config(text=text))
    except Exception:
        pass

def set_buttons_enabled(enabled: bool):
    def apply():
        download_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
        open_folder_button.config(state=tk.NORMAL if enabled else tk.DISABLED)
    try:
        status_label.after(0, apply)
    except Exception:
        pass

def show_info(title, message):
    try:
        status_label.after(0, lambda: messagebox.showinfo(title, message))
    except Exception:
        pass

def show_error(title, message):
    try:
        status_label.after(0, lambda: messagebox.showerror(title, message))
    except Exception:
        pass

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

def extract_iframe_urls(html_text, base_url):
    urls = []
    for m in re.finditer(r'<iframe[^>]+src=["\']?([^"\'>\s]+)', html_text, flags=re.IGNORECASE):
        src = m.group(1).strip()
        if src:
            urls.append(urljoin(base_url, src))

    legacy_match = re.search(r'src=["\'](https?://fplayer\.cc/embed/[^"\']+)', html_text, flags=re.IGNORECASE)
    if legacy_match:
        urls.insert(0, legacy_match.group(1))

    legacy_match_2 = re.search(r'src=(https?://fplayer\.cc/embed/[^\s>]+)', html_text, flags=re.IGNORECASE)
    if legacy_match_2:
        urls.insert(0, legacy_match_2.group(1))

    seen = set()
    ordered = []
    for u in urls:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ordered

def extract_media_urls(text, base_url):
    results = []
    patterns = [
        r'(https?:\\?/\\?/[^\'"\s]+?\.(?:m3u8|mp4)(?:\?[^\'"\s]*)?)',
        r'(//[^\'"\s]+?\.(?:m3u8|mp4)(?:\?[^\'"\s]*)?)',
        r'(["\'])([^"\']+?\.(?:m3u8|mp4)(?:\?[^"\']*)?)\1',
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = m.group(2) if m.lastindex and m.lastindex >= 2 else m.group(1)
            if not raw:
                continue
            url = raw.replace("\\/", "/").replace("\\u0026", "&").strip()
            if url.startswith("//"):
                url = urljoin(base_url, url)
            elif url.startswith("/"):
                url = urljoin(base_url, url)
            if url.lower().startswith(("http://", "https://")):
                results.append(url)

    seen = set()
    ordered = []
    for u in results:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ordered

def pick_best_media_url(urls):
    if not urls:
        return None
    mp4s = [u for u in urls if ".mp4" in u.lower()]
    if mp4s:
        return mp4s[0]
    m3u8s = [u for u in urls if ".m3u8" in u.lower()]
    if m3u8s:
        return m3u8s[0]
    return urls[0]

def extract_with_ytdlp(target_url, referer_url):
    try:
        ydl_opts = {
            'quiet': True,
            'skip_download': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0',
                'Referer': referer_url,
            },
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(target_url, download=False)
        if not info:
            return None
        if isinstance(info, dict) and info.get('entries'):
            info = next((e for e in info['entries'] if e), None)
        if not info:
            return None
        if isinstance(info, dict):
            if info.get('url'):
                return info['url']
            requested_formats = info.get('requested_formats') or []
            for fmt in requested_formats:
                u = fmt.get('url') if isinstance(fmt, dict) else None
                if u:
                    return u
        return None
    except Exception:
        return None

def find_video_url(page_url):
    try:
        session = requests.Session()
        base_headers = {
            'User-Agent': 'Mozilla/5.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        set_status("第1/3步: 正在获取主页面...")
        main_page_response = session.get(page_url, headers=base_headers, timeout=20)
        main_page_response.raise_for_status()

        set_status("第2/3步: 正在查找播放器...")
        main_text = main_page_response.text
        media_urls = extract_media_urls(main_text, page_url)
        best = pick_best_media_url(media_urls)
        if best:
            return best, page_url

        iframe_urls = extract_iframe_urls(main_text, page_url)
        if not iframe_urls:
            set_status("错误: 找不到视频播放器。")
            return None

        set_status("第3/3步: 正在提取视频链接...")
        for iframe_url in iframe_urls:
            try:
                iframe_response = session.get(
                    iframe_url,
                    headers={**base_headers, 'Referer': page_url},
                    timeout=20
                )
                iframe_response.raise_for_status()
                iframe_media_urls = extract_media_urls(iframe_response.text, iframe_url)
                best = pick_best_media_url(iframe_media_urls)
                if best:
                    return best, iframe_url
            except requests.exceptions.RequestException:
                continue

        set_status("正在尝试使用 yt-dlp 解析...")
        ytdlp_url = extract_with_ytdlp(page_url, page_url)
        if ytdlp_url:
            return ytdlp_url, page_url
        for iframe_url in iframe_urls:
            ytdlp_url = extract_with_ytdlp(iframe_url, page_url)
            if ytdlp_url:
                return ytdlp_url, iframe_url

        set_status("错误: 找到播放器但无法提取链接。")
        return None

    except requests.exceptions.RequestException as e:
        set_status(f"网络错误: {e}")
        return None
    except Exception as e:
        set_status(f"发生未知错误: {e}")
        return None

def start_download():
    page_url = url_entry.get()
    if not page_url:
        messagebox.showerror("错误", "请输入网页地址")
        return

    set_buttons_enabled(False)
    set_status("任务开始...")
    
    threading.Thread(target=download_video, args=(page_url,), daemon=True).start()

def download_video(page_url):
    found = find_video_url(page_url)

    if not found:
        set_status("无法找到视频链接，请尝试其他地址。")
        set_buttons_enabled(True)
        return
    
    video_url, referer_url = found
    parsed_referer = urlparse(referer_url)
    origin = f"{parsed_referer.scheme}://{parsed_referer.netloc}" if parsed_referer.scheme and parsed_referer.netloc else None

    set_status("已找到链接！准备开始下载...")

    try:
        ydl_opts = {
            'progress_hooks': [hook],
            'paths': {'home': DOWNLOAD_PATH},
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'http_headers': {
                'User-Agent': 'Mozilla/5.0',
                'Referer': referer_url,
                **({'Origin': origin} if origin else {}),
            },
            'windowsfilenames': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        set_status("下载完成！")
        show_info("成功", f"视频已成功下载到:\n{DOWNLOAD_PATH}")
    except Exception as e:
        set_status(f"下载出错: {e}")
        show_error("错误", f"下载视频失败。\n{e}")
    finally:
        set_buttons_enabled(True)

def hook(d):
    if d['status'] == 'downloading':
        percent_str = d['_percent_str'].strip()
        speed_str = d.get('_speed_str', '').strip()
        eta_str = d.get('_eta_str', '').strip()
        set_status(f"正在下载: {percent_str} (速度: {speed_str}) 剩余时间: {eta_str}")
    elif d['status'] == 'finished':
        set_status("下载完成，正在处理...")

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
