TRANSLATIONS = {
    "zh": {
        "title": "91pinse下载器",
        "url_label": "网页地址:",
        "download_button": "解析并下载",
        "open_folder_button": "打开下载目录",
        "status_prompt": "请输入网页地址，然后点击下载。",
        "error_title": "错误",
        "success_title": "成功",
        "empty_url_error": "请输入网页地址",
        "unable_open_folder": "无法打开下载文件夹。",
        "step1_fetching": "第1/3步: 正在获取主页面...",
        "step2_finding": "第2/3步: 正在查找播放器...",
        "error_player_not_found": "错误: 找不到视频播放器。",
        "step3_extracting": "第3/3步: 正在提取视频链接...",
        "trying_ytdlp": "正在尝试使用 yt-dlp 解析...",
        "error_extract_failed": "错误: 找到播放器但无法提取链接。",
        "network_error": "网络错误: {error}",
        "unknown_error": "发生未知错误: {error}",
        "task_start": "任务开始...",
        "unable_find_link": "无法找到视频链接，请尝试其他地址。",
        "found_link": "已找到链接！准备开始下载...",
        "download_complete": "下载完成！",
        "video_saved": "视频已成功下载到:\n{path}",
        "download_error": "下载出错: {error}",
        "failed_download": "下载视频失败。",
        "downloading_status": "正在下载: {percent} (速度: {speed}) 剩余时间: {eta}",
        "processing": "下载完成，正在处理..."
    },
    "en": {
        "title": "91pinse Downloader",
        "url_label": "Webpage URL:",
        "download_button": "Parse and Download",
        "open_folder_button": "Open Download Folder",
        "status_prompt": "Please enter a webpage URL, then click Download.",
        "error_title": "Error",
        "success_title": "Success",
        "empty_url_error": "Please enter a webpage URL.",
        "unable_open_folder": "Unable to open the download folder.",
        "step1_fetching": "Step 1/3: Fetching webpage...",
        "step2_finding": "Step 2/3: Looking for video player...",
        "error_player_not_found": "Error: Video player not found.",
        "step3_extracting": "Step 3/3: Extracting video URL...",
        "trying_ytdlp": "Trying to extract using yt-dlp...",
        "error_extract_failed": "Error: Found the player but couldn't extract the video link.",
        "network_error": "Network error: {error}",
        "unknown_error": "An unknown error occurred: {error}",
        "task_start": "Starting task...",
        "unable_find_link": "Unable to find the video link. Please try another URL.",
        "found_link": "Video link found! Preparing to download...",
        "download_complete": "Download complete!",
        "video_saved": "The video has been successfully downloaded to:\n{path}",
        "download_error": "Download error: {error}",
        "failed_download": "Failed to download the video.",
        "downloading_status": "Downloading: {percent} (Speed: {speed}) Time remaining: {eta}",
        "processing": "Download complete. Processing..."
    }
}

DEFAULT_LANGUAGE = "zh"

def get_translation(lang, key):
    return TRANSLATIONS.get(lang, TRANSLATIONS[DEFAULT_LANGUAGE]).get(key, key)
