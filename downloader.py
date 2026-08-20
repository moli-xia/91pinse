import tkinter as tk
from tkinter import messagebox
import yt_dlp
import threading
import re
import requests
import os
import subprocess
import sys
import base64
from urllib.parse import urljoin, urlparse

import translations

LANGUAGE = translations.DEFAULT_LANGUAGE


def translate(key, **kwargs):
    text = translations.get_translation(LANGUAGE, key)
    try:
        return text.format(**kwargs) if kwargs else text
    except Exception:
        return text


def set_language(lang):
    global LANGUAGE
    if lang in translations.TRANSLATIONS:
        LANGUAGE = lang
        update_ui_texts()


def update_ui_texts():
    root.title(translate("title"))
    url_label.config(text=translate("url_label"))
    download_button.config(text=translate("download_button"))
    open_folder_button.config(text=translate("open_folder_button"))
    status_label.config(text=translate("status_prompt"))


def get_download_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

DOWNLOAD_PATH = get_download_path()

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)

BASE_HEADERS = {
    'User-Agent': DEFAULT_USER_AGENT,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}

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
        messagebox.showerror(translate("error_title"), translate("unable_open_folder") + f"\n{e}")

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
            url = (
                raw.replace("\\u002F", "/")
                .replace("\\/", "/")
                .replace("\\u0026", "&")
                .strip()
            )
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

def extract_base64_media_urls(text, base_url):
    results = []
    encoded_values = re.findall(r'["\']([A-Za-z0-9+/\\=]{24,})["\']', text)
    for raw_value in encoded_values:
        normalized = raw_value.replace("\\u003D", "=").replace("\\/", "/")
        try:
            decoded = base64.b64decode(normalized).decode("utf-8", "ignore")
        except Exception:
            continue
        results.extend(extract_media_urls(decoded, base_url))

    seen = set()
    ordered = []
    for u in results:
        if u not in seen:
            ordered.append(u)
            seen.add(u)
    return ordered

def is_placeholder_media_url(url):
    lowered = url.lower()
    return (
        '{' in url or
        '}' in url or
        'ping.m3u8' in lowered or
        lowered.startswith('blob:')
    )

def pick_best_media_url(urls):
    if not urls:
        return None

    candidates = [u for u in urls if not is_placeholder_media_url(u)]
    if not candidates:
        candidates = urls

    def score(url):
        lowered = url.lower()
        value = 0
        if '.m3u8' in lowered:
            value += 300
        elif '.mp4' in lowered:
            value += 200
        if 'master.m3u8' in lowered:
            value += 120
        if 'expires=' in lowered:
            value += 60
        if 'trailer' in lowered:
            value -= 400
        if 'preview' in lowered or 'thumb' in lowered:
            value -= 150
        return value

    return max(candidates, key=score)

def extract_with_ytdlp(target_url, referer_url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'http_headers': {
                **BASE_HEADERS,
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

        set_status(translate("step1_fetching"))
        main_page_response = session.get(page_url, headers=BASE_HEADERS, timeout=20)
        main_page_response.raise_for_status()
        final_page_url = main_page_response.url or page_url

        set_status(translate("step2_finding"))
        main_text = main_page_response.text
        media_urls = extract_media_urls(main_text, final_page_url)
        media_urls.extend(extract_base64_media_urls(main_text, final_page_url))
        best = pick_best_media_url(media_urls)
        if best:
            return best, final_page_url

        iframe_urls = extract_iframe_urls(main_text, final_page_url)
        if not iframe_urls:
            set_status(translate("error_player_not_found"))
            return None

        set_status(translate("step3 extracting"))
        for iframe_url in iframe_urls:
            try:
                iframe_response = session.get(
                    iframe_url,
                    headers={**BASE_HEADERS, 'Referer': final_page_url},
                    timeout=20
                )
                iframe_response.raise_for_status()
                iframe_media_urls = extract_media_urls(iframe_response.text, iframe_url)
                iframe_media_urls.extend(extract_base64_media_urls(iframe_response.text, iframe_url))
                best = pick_best_media_url(iframe_media_urls)
                if best:
                    return best, iframe_url
            except requests.exceptions.RequestException:
                continue

        set_status(translate("trying_ytdlp"))
        ytdlp_url = extract_with_ytdlp(final_page_url, final_page_url)
        if ytdlp_url:
            return ytdlp_url, final_page_url
        for iframe_url in iframe_urls:
            ytdlp_url = extract_with_ytdlp(iframe_url, final_page_url)
            if ytdlp_url:
                return ytdlp_url, iframe_url

        set_status(translate("error extract_failed"))
        return None

    except requests.exceptions.RequestException as e:
        set_status(translate("network error", error=e))
        return None
    except Exception as e:
        set_status(translate("unknown error", error=e))
        return None

def start_download():
    page_url = url_entry.get()
    if not page_url:
        messagebox.showerror(translate("error title"), translate("empty url_error"))
        return

    set_buttons_enabled(False)
    set_status(translate("task_start"))
    
    threading.Thread(target=download_video, args=(page_url,), daemon=True).start()

def download_video(page_url):
    found = find_video_url(page_url)

    if not found:
        set_status(translate("unable_find_link"))
        set_buttons_enabled(True)
        return
    
    video_url, referer_url = found
    parsed_referer = urlparse(referer_url)
    origin = f"{parsed_referer.scheme}://{parsed_referer.netloc}" if parsed_referer.scheme and parsed_referer.netloc else None

    set_status(translate("found_link"))

    try:
        ydl_opts = {
            'progress_hooks': [hook],
            'paths': {'home': DOWNLOAD_PATH},
            'outtmpl': os.path.join(DOWNLOAD_PATH, '%(title)s.%(ext)s'),
            'http_headers': {
                **BASE_HEADERS,
                'Referer': referer_url,
                **({'Origin': origin} if origin else {}),
            },
            'windowsfilenames': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])

        set_status(translate("download_complete"))
        show_info(translate("success_title"), translate("video_saved", path=DOWNLOAD_PATH))
    except Exception as e:
        set_status(translate("download_error", error=e))
        show_error(translate("error_title"), translate("failed_download") + f"\n{e}")
    finally:
        set_buttons_enabled(True)

def hook(d):
    if d['status'] == 'downloading':
        percent_str = d['_percent_str'].strip()
        speed_str = d.get('_speed_str', '').strip()
        eta_str = d.get('_eta_str', '').strip()
        set_status(translate("downloading_status", percent=percent_str, speed=speed_str, eta=eta_str))
    elif d['status'] == 'finished':
        set_status(translate("processing"))

# --- GUI Setup ---
root = tk.Tk()

frame = tk.Frame(root, padx=10, pady=10)
frame.pack(padx=10, pady=10)

url_label = tk.Label(frame, text=translate("url_label"))
url_label.pack(pady=(0, 5))

url_entry = tk.Entry(frame, width=60)
url_entry.pack(pady=5)

button_frame = tk.Frame(frame)
button_frame.pack(pady=10)

download_button = tk.Button(button_frame, text=translate("download_button"), command=start_download)
download_button.pack(side=tk.LEFT, padx=5)

open_folder_button = tk.Button(button_frame, text=translate("open_folder_button"), command=open_download_folder)
open_folder_button.pack(side=tk.LEFT, padx=5)

lang_button_zh = tk.Button(button_frame, text="中文", command=lambda: set_language("zh"))
lang_button_zh.pack(side=tk.LEFT, padx=5)

lang_button_en = tk.Button(button_frame, text="English", command=lambda: set_language("en"))
lang_button_en.pack(side=tk.LEFT, padx=5)

status_label = tk.Label(frame, text=translate("status_prompt"), wraplength=400, justify=tk.LEFT)
status_label.pack(pady=5)

update_ui_texts()
root.mainloop()
