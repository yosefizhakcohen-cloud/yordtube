import os
import threading
import sys
import webview
import yt_dlp
import re
import json
import urllib.request
import webbrowser
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HANDLE

kernel32.GlobalLock.argtypes = [wintypes.HANDLE]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HANDLE]
kernel32.GlobalUnlock.restype = wintypes.BOOL

CF_UNICODETEXT = 13

def get_clipboard_text():
    if not user32.OpenClipboard(None):
        return None
    try:
        h_clip_mem = user32.GetClipboardData(CF_UNICODETEXT)
        if not h_clip_mem:
            return None
        p_clip_mem = kernel32.GlobalLock(h_clip_mem)
        if not p_clip_mem:
            return None
        try:
            text = ctypes.wstring_at(p_clip_mem)
            return text
        finally:
            kernel32.GlobalUnlock(h_clip_mem)
    finally:
        user32.CloseClipboard()

def is_youtube_url(text):
    if not text:
        return False
    text = text.strip()
    return bool(re.match(r'^https?://(www\.)?(youtube\.com|youtu\.be|m\.youtube\.com)/', text, re.IGNORECASE))

SETTINGS_DIR = os.path.join(os.getenv('APPDATA', os.path.expanduser('~')), 'YouTubeDownloaderGemini')
SETTINGS_FILE = os.path.join(SETTINGS_DIR, 'settings.json')

def load_settings():
    default_save = os.path.join(os.path.expanduser('~'), 'Music')
    defaults = {
        'save_dir': default_save,
        'theme': 'light',
        'play_sound': True,
        'deep_search': False,
        'bypass_ssl': False,
        'netfree_mode': False,
        'video_quality': 'best',
        'ad_source_url': 'https://gist.githubusercontent.com/yosefizhakcohen-cloud/da5cada150b977263846d74d199cb211/raw/gistfile1.txt',
        'status_url': 'https://gist.githubusercontent.com/yosefizhakcohen-cloud/da5cada150b977263846d74d199cb211/raw/status.txt',
        'organize_by_playlists': False
    }
    if not os.path.exists(SETTINGS_DIR):
        try:
            os.makedirs(SETTINGS_DIR)
        except Exception:
            pass
    
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ensure all keys exist
                for k, v in defaults.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception:
            pass
    return defaults

def save_settings(settings):
    if not os.path.exists(SETTINGS_DIR):
        try:
            os.makedirs(SETTINGS_DIR)
        except Exception:
            pass
    try:
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print("Error saving settings:", e)

class Api:
    def __init__(self):
        self._window = None
        self.settings = load_settings()
        self._downloading = False
        self._cancel_requested = False
        self._current_download_filename = None
        self._current_index = 0
        self._total_files = 0
        self._current_title = ""

    def set_window(self, window):
        self._window = window
        self.start_clipboard_monitor()

    def start_clipboard_monitor(self):
        def loop():
            import time
            last_url = None
            while True:
                time.sleep(0.3)
                try:
                    text = get_clipboard_text()
                    if text:
                        text_stripped = text.strip()
                        if text_stripped != last_url and is_youtube_url(text_stripped):
                            last_url = text_stripped
                            if self._window:
                                try:
                                    self._window.restore()
                                except Exception:
                                    pass
                                try:
                                    self._window.show()
                                except Exception:
                                    pass
                                try:
                                    self._window.on_top = True
                                    self._window.on_top = False
                                except Exception:
                                    pass
                                url_js = json.dumps(text_stripped)
                                self._window.evaluate_js(f"onYoutubeLinkCopied({url_js})")
                except Exception as e:
                    print("Clipboard monitor error:", e)
        
        thread = threading.Thread(target=loop)
        thread.daemon = True
        thread.start()

    def get_settings(self):
        return self.settings

    def save_settings_api(self, settings_dict):
        self.settings.update(settings_dict)
        save_settings(self.settings)
        return True

    def reset_settings(self):
        default_save = os.path.join(os.path.expanduser('~'), 'Music')
        self.settings = {
            'save_dir': default_save,
            'theme': 'light',
            'play_sound': True,
            'deep_search': False,
            'bypass_ssl': False,
            'netfree_mode': False,
            'video_quality': 'best',
            'ad_source_url': 'https://gist.githubusercontent.com/yosefizhakcohen-cloud/da5cada150b977263846d74d199cb211/raw/gistfile1.txt',
            'status_url': 'https://gist.githubusercontent.com/yosefizhakcohen-cloud/da5cada150b977263846d74d199cb211/raw/status.txt'
        }
        save_settings(self.settings)
        return self.settings

    def get_ad_data(self):
        url = self.settings.get('ad_source_url', '')
        if not url:
            return {"active": False}
        try:
            import time
            import ssl
            context = ssl._create_unverified_context()
            cache_buster_url = f"{url}?t={int(time.time())}"
            req = urllib.request.Request(cache_buster_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"Error fetching ads: {e}")
            return {"active": False}

    def check_app_status(self):
        url = self.settings.get('status_url', '')
        if not url:
            return {"status": "ok"}
        try:
            import time
            import ssl
            context = ssl._create_unverified_context()
            cache_buster_url = f"{url}?t={int(time.time())}"
            req = urllib.request.Request(cache_buster_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=5, context=context) as response:
                content = response.read().decode('utf-8').strip()
                # If the content is exactly 'true' (case-insensitive), it's active
                if content.lower() == 'true':
                    return {"status": "ok"}
                # If the content is 'plus', block with a default message
                elif 'plus' in content.lower():
                    return {
                        "status": "blocked",
                        "message": "403 - התוכנה בהרחבה זמנית!<br><br>על מנת להמשיך להשתמש בתוכנה, אנא הורד את העדכון האחרון בפורום מתמחים טופ."
                    }
                # If it's anything else (but not empty), block and show that text as the message!
                elif content:
                    return {
                        "status": "blocked",
                        "message": content
                    }
            return {"status": "ok"}
        except Exception as e:
            print(f"Error checking app status: {e}")
            # If offline or error, let them play safe (don't block)
            return {"status": "ok"}

    def open_link(self, url):
        try:
            webbrowser.open(url)
            return True
        except Exception as e:
            print(f"Error opening link: {e}")
            return False

    def diagnose_network(self):
        import socket
        import urllib.request
        import ssl
        import time
        
        results = {
            'internet': False,
            'dns_youtube': False,
            'ssl_verify': False,
            'filter_type': 'unfiltered', # 'netfree', 'rimon_etrog', 'unfiltered'
            'youtube_access': False,
            'details': []
        }
        
        # Test 1: General Internet (DNS lookup for a public service)
        try:
            socket.gethostbyname('one.one.one.one')
            results['internet'] = True
            results['details'].append("✅ חיבור בסיסי לרשת פעיל.")
        except Exception:
            results['details'].append("❌ שגיאה: אין חיבור לרשת או ששירותי ה-DNS חסומים.")
            return results
            
        # Test 2: DNS lookup for YouTube
        try:
            socket.gethostbyname('www.youtube.com')
            results['dns_youtube'] = True
            results['details'].append("✅ פיענוח כתובת יוטיוב (DNS) הצליח.")
        except Exception:
            results['details'].append("❌ שגיאה: לא ניתן לפענח את הכתובת של יוטיוב (ייתכן שהסינון חוסם אותה ברמת ה-DNS).")
            
        # Test 3: SSL Handshake to a standard secure site (e.g. google.com) with system verification
        try:
            req = urllib.request.Request('https://www.google.com', headers={'User-Agent': 'Mozilla/5.0'})
            # We use default SSL context (which verifies certificates)
            with urllib.request.urlopen(req, timeout=5) as r:
                pass
            results['ssl_verify'] = True
            results['details'].append("✅ אימות תעודות אבטחה (SSL) תקין ומאופשר.")
        except urllib.error.URLError as e:
            if "CERTIFICATE_VERIFY_FAILED" in str(e):
                results['details'].append("❌ שגיאה: אימות תעודת אבטחה (SSL) נכשל. תעודת הסינון אינה מותקנת במחשבך עבור פייתון. (פיתרון: מומלץ להפעיל 'עוקף SSL' בהגדרות התוכנה!)")
            else:
                results['details'].append(f"❌ שגיאת תקשורת מאובטחת (SSL): {str(e)}")
        except Exception as e:
            results['details'].append(f"❌ שגיאת תקשורת כללית: {str(e)}")

        # Test 4: Check if NetFree is active
        try:
            req = urllib.request.Request('https://check.netfree.link/test', headers={'User-Agent': 'Mozilla/5.0'})
            ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req, timeout=3, context=ctx) as r:
                body = r.read().decode('utf-8', errors='ignore')
                if "netfree" in body.lower():
                    results['filter_type'] = 'netfree'
                    results['details'].append("🛡️ סינון האינטרנט הפעיל זוהה כ-נטפרי.")
        except Exception:
            pass

        # If not netfree, check for Etrog/Rimon
        if results['filter_type'] == 'unfiltered':
            try:
                # Request a known video page or general youtube page
                req = urllib.request.Request('https://www.youtube.com', headers={'User-Agent': 'Mozilla/5.0'})
                ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                    content = r.read().decode('utf-8', errors='ignore')
                    final_url = r.geturl()
                    
                    if "rimon" in final_url.lower() or "etrog" in final_url.lower() or "block" in final_url.lower() or "internet-filter" in content.lower():
                        results['filter_type'] = 'rimon_etrog'
                        results['details'].append("🛡️ סינון האינטרנט הפעיל זוהה כ-רימון/אתרוג (זוהה דף חסימה או ניתוב מחדש).")
                    else:
                        results['youtube_access'] = True
                        results['details'].append("✅ חיבור ישיר ליוטיוב הצליח בהצלחה.")
            except Exception as e:
                err_str = str(e)
                if "403" in err_str or "418" in err_str or "forbidden" in err_str.lower():
                    results['filter_type'] = 'rimon_etrog'
                    results['details'].append("🛡️ סינון האינטרנט הפעיל זוהה כ-רימון/אתרוג (הגישה ליוטיוב חסומה על ידי הסינון).")
                else:
                    results['details'].append(f"❌ שגיאה בגישה ליוטיוב: {err_str}")
        else:
            # If NetFree was detected, check if we can access youtube
            try:
                req = urllib.request.Request('https://www.youtube.com', headers={'User-Agent': 'Mozilla/5.0'})
                ctx = ssl._create_unverified_context()
                with urllib.request.urlopen(req, timeout=5, context=ctx) as r:
                    results['youtube_access'] = True
                    results['details'].append("✅ חיבור ליוטיוב תחת סינון נטפרי פעיל (דף הבית נגיש).")
            except Exception as e:
                results['details'].append("⚠️ שים לב: דף הבית של יוטיוב חסום בנטפרי, אך ניתן להוריד סרטונים שאושרו ישירות באמצעות קישור ישיר.")

        return results

    def select_save_dir(self):
        if not self._window:
            return None
        res = self._window.create_file_dialog(
            webview.FOLDER_DIALOG, 
            directory=self.settings.get('save_dir')
        )
        if res and len(res) > 0:
            path = res[0]
            self.settings['save_dir'] = path
            save_settings(self.settings)
            return path
        return None

    def cancel_download(self):
        self._cancel_requested = True
        return True

    def inspect_url(self, url):
        # If it is a channel URL, ensure it targets the videos/playlists tab based on setting
        url_lower = url.lower()
        is_channel_url = '/@' in url_lower or '/channel/' in url_lower or '/c/' in url_lower or '/user/' in url_lower
        org_by_playlists = self.settings.get('organize_by_playlists', False)

        if is_channel_url:
            if org_by_playlists:
                if not any(url_lower.endswith(tab) for tab in ['/videos', '/shorts', '/live', '/playlists', '/featured']):
                    base_channel = url.split('/playlists')[0].split('/videos')[0].split('/shorts')[0].split('/live')[0].split('/featured')[0].rstrip('/')
                    url = base_channel + '/playlists'
            else:
                if not any(url_lower.endswith(tab) for tab in ['/videos', '/shorts', '/live', '/playlists', '/featured']):
                    url = url.rstrip('/') + '/videos'

        qjs_binary = resource_path('qjs.exe')
        js_runtimes_config = {}
        if os.path.exists(qjs_binary):
            js_runtimes_config['quickjs'] = {'path': qjs_binary}
        elif os.path.exists('qjs.exe'):
            js_runtimes_config['quickjs'] = {'path': os.path.abspath('qjs.exe')}

        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'skip_download': True,
            'nocheckcertificate': True,
            'socket_timeout': 15,
            'extractor_args': {'youtube': ['player_client=ios,tv_embedded,android,web']}
        }
        if js_runtimes_config:
            ydl_opts['js_runtimes'] = js_runtimes_config
        
        # If it is a channel URL, limit to 1000 videos (or 5000 if deep search is enabled)
        if is_channel_url:
            ydl_opts['playlistend'] = 5000 if self.settings.get('deep_search') else 1000
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception as e:
                    err_msg = str(e).lower()
                    if is_channel_url and ('does not have a' in err_msg or 'tab' in err_msg or 'not found' in err_msg or 'unviewable' in err_msg):
                        base_channel = url.split('/playlists')[0].split('/videos')[0].split('/shorts')[0].split('/live')[0].split('/featured')[0].rstrip('/')
                        url = base_channel
                        info = ydl.extract_info(url, download=False)
                    else:
                        raise e
                
                # If it's a playlist or a channel
                if info and (info.get('_type') == 'playlist' or 'entries' in info):
                    # Check if it is a channel based on metadata
                    is_channel = is_channel_url
                    avatar_url = None
                    if info.get('thumbnails'):
                        for thumb in info['thumbnails']:
                            if thumb.get('id') == 'avatar_uncropped':
                                avatar_url = thumb.get('url')
                                is_channel = True
                                break
                                
                        if not avatar_url and is_channel:
                            # Fallback: search for any square thumbnail
                            for thumb in info['thumbnails']:
                                if thumb.get('width') == thumb.get('height') and thumb.get('width') is not None:
                                    avatar_url = thumb.get('url')
                                    break

                    entries = []
                    
                    if is_channel and url.endswith('/playlists'):
                        playlist_video_ids = set()
                        raw_entries = info.get('entries', [])
                        
                        for pl in raw_entries:
                            if not pl:
                                continue
                            pl_title = pl.get('title')
                            pl_url = pl.get('url')
                            if not pl_url:
                                continue
                                
                            try:
                                pl_opts = ydl_opts.copy()
                                pl_opts['playlistend'] = 1000
                                with yt_dlp.YoutubeDL(pl_opts) as pl_ydl:
                                    pl_info = pl_ydl.extract_info(pl_url, download=False)
                                    for entry in pl_info.get('entries', []):
                                        if not entry:
                                            continue
                                        video_id = entry.get('id')
                                        playlist_video_ids.add(video_id)
                                        
                                        video_url = entry.get('url')
                                        if video_url and not video_url.startswith('http'):
                                            video_url = f"https://www.youtube.com/watch?v={video_url}"
                                        elif not video_url:
                                            video_url = f"https://www.youtube.com/watch?v={video_id}"
                                            
                                        thumb_url = ""
                                        if entry.get('thumbnails'):
                                            thumb_url = entry['thumbnails'][-1].get('url') or ""
                                        elif entry.get('thumbnail'):
                                            thumb_url = entry.get('thumbnail') or ""
                                            
                                        entries.append({
                                            'id': video_id,
                                            'title': f"[{pl_title}] {entry.get('title')}",
                                            'url': video_url,
                                            'thumbnail': thumb_url,
                                            'playlist_title': pl_title
                                        })
                            except Exception as pl_err:
                                print(f"Error extracting playlist {pl_title}: {pl_err}")
                                
                        # Extract loose videos from flat uploads page to make sure nothing is missed
                        try:
                            base_channel = url.split('/playlists')[0].rstrip('/')
                            uploads_url = base_channel + '/videos'
                            uploads_info = ydl.extract_info(uploads_url, download=False)
                            for entry in uploads_info.get('entries', []):
                                if not entry:
                                    continue
                                video_id = entry.get('id')
                                if video_id not in playlist_video_ids:
                                    video_url = entry.get('url')
                                    if video_url and not video_url.startswith('http'):
                                        video_url = f"https://www.youtube.com/watch?v={video_url}"
                                    elif not video_url:
                                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                                        
                                    thumb_url = ""
                                    if entry.get('thumbnails'):
                                        thumb_url = entry['thumbnails'][-1].get('url') or ""
                                    elif entry.get('thumbnail'):
                                        thumb_url = entry.get('thumbnail') or ""
                                        
                                    entries.append({
                                        'id': video_id,
                                        'title': entry.get('title'),
                                        'url': video_url,
                                        'thumbnail': thumb_url,
                                        'playlist_title': None
                                    })
                        except Exception as uploads_err:
                            print(f"Error fetching loose videos: {uploads_err}")
                    else:
                        raw_entries = info.get('entries', [])
                        for entry in raw_entries:
                            if entry:
                                video_url = entry.get('url')
                                if video_url and not video_url.startswith('http'):
                                    video_url = f"https://www.youtube.com/watch?v={video_url}"
                                elif not video_url:
                                    video_url = f"https://www.youtube.com/watch?v={entry.get('id')}"
                                
                                thumb_url = ""
                                if entry.get('thumbnails'):
                                    thumb_url = entry['thumbnails'][-1].get('url') or ""
                                elif entry.get('thumbnail'):
                                    thumb_url = entry.get('thumbnail') or ""
                                    
                                entries.append({
                                    'id': entry.get('id'),
                                    'title': entry.get('title') or ("סרטון מתוך ערוץ" if is_channel else "שיר מתוך פלייליסט"),
                                    'url': video_url,
                                    'thumbnail': thumb_url
                                })
                            
                    if is_channel:
                        title = info.get('title') or info.get('uploader') or 'ערוץ ללא שם'
                        if title.startswith('Uploads from '):
                            title = title[len('Uploads from '):]
                        # Clean up "- Videos", "- Shorts", "- Live", "- Featured", "- Playlists", "- Topic" from title
                        for suffix in [' - Videos', ' - Shorts', ' - Live', ' - Featured', ' - Playlists', ' - Topic']:
                            if title.endswith(suffix):
                                title = title[:-len(suffix)]
                                
                        return {
                            'type': 'channel',
                            'title': title,
                            'handle': info.get('uploader_id') or '',
                            'avatar_url': avatar_url or '',
                            'entries': entries
                        }
                    else:
                        return {
                            'type': 'playlist',
                            'title': info.get('title') or 'פלייליסט ללא שם',
                            'entries': entries
                        }
                else:
                    return {
                        'type': 'video',
                        'title': (info.get('title') if info else 'סרטון יוטיוב') or 'סרטון יוטיוב',
                        'url': url
                    }
        except Exception as e:
            err_str = str(e)
            if "418" in err_str:
                msg = "הסרטון חסום לצפייה על ידי סינון האינטרנט שלך (נטפרי - 418 Blocked)."
            elif "403" in err_str or "forbidden" in err_str.lower():
                msg = "שגיאת גישה ליוטיוב (403 Forbidden). נסה להוריד שוב."
            elif "private" in err_str.lower():
                msg = "הסרטון או הפלייליסט מוגדרים כפרטיים ולא ניתנים להורדה."
            elif "does not exist" in err_str.lower() or "unavailable" in err_str.lower():
                msg = "הסרטון או הערוץ אינם קיימים או שאינם זמינים ביוטיוב."
            elif "failed to extract any player response" in err_str.lower():
                msg = "הגישה לתוכן הסרטון נכשלה. ייתכן שהסרטון חסום בסינון או דורש אימות גיל."
            elif "ssl" in err_str.lower() or "certificate verify failed" in err_str.lower():
                msg = "שגיאת אבטחת SSL. אנא ודא שתעודת האבטחה של הסינון מותקנת במחשבך."
            elif "timed out" in err_str.lower() or "timeout" in err_str.lower():
                msg = "פג זמן החיבור לשרת (Timeout). ייתכן שיש בעיית תקשורת."
            else:
                msg = f"{err_str}"
            return {
                'type': 'error',
                'message': msg
            }

    def progress_hook(self, d):
        if self._cancel_requested:
            raise Exception("cancelled")
            
        status = d.get('status')
        if status == 'downloading':
            try:
                # Robustly determine file percentage
                file_percent = 0.0
                downloaded = d.get('downloaded_bytes') or 0
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                
                if total and total > 0:
                    file_percent = (downloaded / total) * 100.0
                else:
                    raw_p = d.get('_percent_str')
                    if raw_p:
                        clean_p = re.sub(r'\x1b\[[0-9;]*m', '', str(raw_p)).replace('%', '').strip()
                        try:
                            file_percent = float(clean_p)
                        except Exception:
                            file_percent = 0.0
                
                file_percent = max(0.0, min(100.0, file_percent))
                self._current_download_filename = d.get('filename')
                
                if self._total_files > 1:
                    overall_percent = ((self._current_index - 1) + (file_percent / 100.0)) / self._total_files * 100.0
                    bar_percent = f"{overall_percent:.1f}%"
                    prefix = f"({self._current_index}/{self._total_files}) "
                    text = f"{prefix}מוריד: {self._current_title}... {file_percent:.0f}% (סה\"כ: {overall_percent:.0f}%)"
                else:
                    bar_percent = f"{file_percent:.1f}%"
                    text = f"מוריד: {self._current_title}... {file_percent:.0f}%"
                
                if self._window:
                    percent_js = json.dumps(bar_percent)
                    text_js = json.dumps(text)
                    self._window.evaluate_js(f"updateProgress({percent_js}, {text_js})")
            except Exception as e:
                pass
        elif status == 'finished':
            try:
                if self._total_files > 1:
                    overall_percent = ((self._current_index - 1) + 0.95) / self._total_files * 100.0
                    bar_percent = f"{overall_percent:.1f}%"
                    prefix = f"({self._current_index}/{self._total_files}) "
                    text = f"{prefix}מעבד קובץ: {self._current_title}..."
                else:
                    bar_percent = "95%"
                    text = f"מעבד קובץ: {self._current_title}..."
                if self._window:
                    self._window.evaluate_js(f"updateProgress({json.dumps(bar_percent)}, {json.dumps(text)})")
            except Exception:
                pass

    def postprocessor_hook(self, d):
        if self._cancel_requested:
            raise Exception("cancelled")
        try:
            status = d.get('status')
            postprocessor = d.get('postprocessor', '')
            if status == 'started':
                action_desc = "ממיר ל-MP3..." if "ExtractAudio" in postprocessor else "מעבד תמונה ופרטי שיר..."
                prefix = f"({self._current_index}/{self._total_files}) " if self._total_files > 1 else ""
                text = f"{prefix}{action_desc} ({self._current_title})"
                if self._total_files > 1:
                    overall_percent = ((self._current_index - 1) + 0.98) / self._total_files * 100.0
                    bar_percent = f"{overall_percent:.1f}%"
                else:
                    bar_percent = "98%"
                if self._window:
                    self._window.evaluate_js(f"updateProgress({json.dumps(bar_percent)}, {json.dumps(text)})")
            elif status == 'finished':
                if self._total_files > 1:
                    overall_percent = (self._current_index) / self._total_files * 100.0
                    bar_percent = f"{overall_percent:.1f}%"
                    prefix = f"({self._current_index}/{self._total_files}) "
                    text = f"{prefix}הושלם: {self._current_title}"
                else:
                    bar_percent = "100%"
                    text = f"הושלם: {self._current_title}"
                if self._window:
                    self._window.evaluate_js(f"updateProgress({json.dumps(bar_percent)}, {json.dumps(text)})")
        except Exception:
            pass

    def _download_thread(self, items, format_choice, playlist_title=None):
        try:
            # Handle input format (string, dict, list)
            download_items = []
            if isinstance(items, str):
                download_items.append({'url': items, 'title': 'שיר'})
            elif isinstance(items, dict):
                download_items.append({'url': items.get('url'), 'title': items.get('title', 'שיר')})
            elif isinstance(items, list):
                for x in items:
                    if isinstance(x, str):
                        download_items.append({'url': x, 'title': 'שיר'})
                    elif isinstance(x, dict):
                        download_items.append({
                            'url': x.get('url'),
                            'title': x.get('title', 'שיר'),
                            'playlist_title': x.get('playlist_title')
                        })

            save_base_dir = self.settings.get('save_dir')
            if not os.path.exists(save_base_dir):
                try:
                    os.makedirs(save_base_dir)
                except Exception:
                    save_base_dir = os.path.join(os.path.expanduser('~'), 'Music')

            # Determine output directory
            if playlist_title:
                clean_title = re.sub(r'[\\/*?:"<>|]', "", playlist_title).strip()
                if not clean_title:
                    clean_title = "פלייליסט"
                save_dir = os.path.join(save_base_dir, clean_title)
            else:
                save_dir = save_base_dir

            if not os.path.exists(save_dir):
                try:
                    os.makedirs(save_dir)
                except Exception:
                    save_dir = save_base_dir

            total_files = len(download_items)
            self._total_files = total_files
            success_count = 0
            failed_items = []

            for index, item in enumerate(download_items):
                if self._cancel_requested:
                    break

                self._current_index = index + 1
                self._current_title = item.get('title', 'שיר')
                self._current_download_filename = None
                url = item.get('url')

                item_playlist = item.get('playlist_title')
                if item_playlist:
                    clean_item_playlist = re.sub(r'[\\/*?:"<>|]', "", item_playlist).strip()
                    if not clean_item_playlist:
                        clean_item_playlist = "פלייליסט"
                    item_save_dir = os.path.join(save_base_dir, clean_item_playlist)
                else:
                    item_save_dir = save_dir

                if not os.path.exists(item_save_dir):
                    try:
                        os.makedirs(item_save_dir)
                    except Exception:
                        item_save_dir = save_dir

                if total_files > 1:
                    overall_percent = (index / total_files) * 100.0
                    bar_percent = f"{overall_percent:.1f}%"
                    prefix = f"({self._current_index}/{self._total_files}) "
                    text_val = f"{prefix}מתחיל: {self._current_title}... (סה\"כ: {overall_percent:.0f}%)"
                else:
                    bar_percent = "0%"
                    text_val = f"מתחיל: {self._current_title}... 0%"

                if self._window:
                    self._window.evaluate_js(f"updateProgress({json.dumps(bar_percent)}, {json.dumps(text_val)})")

                # Configure QuickJS runtime if available
                qjs_binary = resource_path('qjs.exe')
                js_runtimes_config = {}
                if os.path.exists(qjs_binary):
                    js_runtimes_config['quickjs'] = {'path': qjs_binary}
                elif os.path.exists('qjs.exe'):
                    js_runtimes_config['quickjs'] = {'path': os.path.abspath('qjs.exe')}

                # Configure ydl options
                ydl_opts = {
                    'outtmpl': os.path.join(item_save_dir, '%(title)s.%(ext)s'),
                    'progress_hooks': [self.progress_hook],
                    'postprocessor_hooks': [self.postprocessor_hook],
                    'noplaylist': True,
                    'quiet': True,
                    'ffmpeg_location': resource_path('.'),
                    'nocheckcertificate': True,
                    'cachedir': False,
                    'continuedl': True,
                    'windowsfilenames': True,
                    'concurrent_fragment_downloads': 2,
                    'retries': 20,
                    'fragment_retries': 20,
                    'skip_unavailable_fragments': True,
                    'socket_timeout': 30,
                    'extractor_args': {'youtube': ['player_client=ios,tv_embedded,android,web']}
                }
                if js_runtimes_config:
                    ydl_opts['js_runtimes'] = js_runtimes_config

                if format_choice == 'mp3':
                    ydl_opts.update({
                        'format': 'bestaudio/best',
                        'writethumbnail': True,
                        'postprocessors': [
                            {
                                'key': 'FFmpegExtractAudio',
                                'preferredcodec': 'mp3',
                                'preferredquality': '192',
                            },
                            {
                                'key': 'EmbedThumbnail',
                            },
                            {
                                'key': 'FFmpegMetadata',
                                'add_metadata': True,
                            }
                        ],
                    })
                elif format_choice == 'nokia':
                    ydl_opts.update({
                        'format': 'best[height<=360]/bestvideo+bestaudio/best',
                        'postprocessors': [{
                            'key': 'FFmpegVideoConvertor',
                            'preferedformat': 'avi',
                        }],
                        'postprocessor_args': {
                            'ffmpeg': ['-s', '320x240', '-vcodec', 'mpeg4', '-acodec', 'libmp3lame', '-b:v', '500k', '-b:a', '128k']
                        }
                    })
                else: # mp4
                    quality = self.settings.get('video_quality', 'best')
                    if quality == '1080':
                        fmt = 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[height<=1080]/best'
                    elif quality == '720':
                        fmt = 'bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best[height<=720]/best'
                    elif quality == '480':
                        fmt = 'bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best[height<=480]/best'
                    else:
                        fmt = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
                    
                    ydl_opts.update({
                        'format': fmt,
                        'merge_output_format': 'mp4',
                    })

                download_success = False
                last_error = None

                # 1. Primary Download Attempt
                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                    download_success = True
                except Exception as e:
                    last_error = e

                # 2. Smart Fallback Attempt if failed and not cancelled
                if not download_success and not self._cancel_requested:
                    err_msg = str(last_error).lower() if last_error else ""
                    if any(x in err_msg for x in ['403', 'forbidden', 'format', 'unavailable', 'extractor', 'signature', 'token']):
                        if self._window:
                            prefix = f"({self._current_index}/{self._total_files}) " if total_files > 1 else ""
                            fb_text = f"{prefix}מנסה ערוץ חלופי עבור {self._current_title}..."
                            self._window.evaluate_js(f"updateProgress({json.dumps(bar_percent)}, {json.dumps(fb_text)})")
                        try:
                            fallback_opts = ydl_opts.copy()
                            if format_choice == 'mp4':
                                fallback_opts['format'] = '18/22/best[ext=mp4]/best'
                            elif format_choice == 'mp3':
                                fallback_opts['format'] = 'bestaudio/best'
                            fallback_opts['extractor_args'] = {'youtube': ['player_client=tv_embedded,ios,mweb']}
                            with yt_dlp.YoutubeDL(fallback_opts) as fallback_ydl:
                                fallback_ydl.download([url])
                            download_success = True
                            last_error = None
                        except Exception as fb_err:
                            last_error = fb_err

                if download_success:
                    success_count += 1
                else:
                    if self._cancel_requested:
                        # Clean up partial download files
                        if self._current_download_filename and os.path.exists(self._current_download_filename):
                            try:
                                os.remove(self._current_download_filename)
                            except Exception:
                                pass
                        if self._current_download_filename:
                            part_file = self._current_download_filename + ".part"
                            if os.path.exists(part_file):
                                try:
                                    os.remove(part_file)
                                except Exception:
                                    pass
                        break
                    else:
                        print("Download error:", last_error)
                        err_str = str(last_error) if last_error else "שגיאה לא ידועה"
                        if "418" in err_str:
                            friendly_err = "חסום בסינון האינטרנט (נטפרי - 418 Blocked)"
                        elif "403" in err_str or "forbidden" in err_str.lower():
                            friendly_err = "שגיאת גישה ליוטיוב (403 Forbidden). נסה שוב או נסה כ-MP3."
                        elif "private" in err_str.lower():
                            friendly_err = "הסרטון מוגדר כפרטי"
                        elif "unavailable" in err_str.lower() or "does not exist" in err_str.lower():
                            friendly_err = "הסרטון אינו זמין או הוסר"
                        elif "failed to extract any player response" in err_str.lower():
                            friendly_err = "הגישה לתוכן הסרטון נכשלה (דורש אימות/חסום)"
                        elif "ssl" in err_str.lower() or "certificate" in err_str.lower():
                            friendly_err = "שגיאת אבטחת SSL (הפעל עוקף SSL בהגדרות)"
                        elif "timed out" in err_str.lower() or "timeout" in err_str.lower():
                            friendly_err = "פג זמן החיבור לשרת (Timeout)"
                        else:
                            friendly_err = err_str
                        
                        failed_items.append({'title': self._current_title, 'error': friendly_err})
                        
                        if total_files == 1:
                            if self._window:
                                msg_js = json.dumps(f"שגיאה בהורדה: {friendly_err}")
                                self._window.evaluate_js(f"downloadFinished(false, {msg_js})")
                            return

            # Completed or broke out of loop
            if self._cancel_requested:
                # Cleanup any partially downloaded files for current item again to be absolutely sure
                if self._current_download_filename and os.path.exists(self._current_download_filename):
                    try:
                        os.remove(self._current_download_filename)
                    except Exception:
                        pass
                if self._current_download_filename:
                    part_file = self._current_download_filename + ".part"
                    if os.path.exists(part_file):
                        try:
                            os.remove(part_file)
                        except Exception:
                            pass
                if self._window:
                    self._window.evaluate_js("downloadFinished(false, 'ההורדה בוטלה על ידי המשתמש.')")
            else:
                if success_count > 0:
                    if total_files == 1:
                        msg = 'ההורדה הסתיימה ונשמרה בהצלחה!'
                    else:
                        msg = f'הורדו בהצלחה {success_count} מתוך {total_files} שירים!'
                        if failed_items:
                            msg += '\n\nהשירים הבאים נכשלו בגלל סינון או שגיאת רשת:'
                            for item in failed_items:
                                msg += f'\n- {item["title"]}: {item["error"]}'
                    if self._window:
                        self._window.evaluate_js(f"downloadFinished(true, {json.dumps(msg)})")
                else:
                    if total_files == 1:
                        msg = 'ההורדה נכשלה.'
                    else:
                        msg = 'ההורדה נכשלה לחלוטין. כל השירים נכשלו:'
                        for item in failed_items:
                            msg += f'\n- {item["title"]}: {item["error"]}'
                    if self._window:
                        self._window.evaluate_js(f"downloadFinished(false, {json.dumps(msg)})")

        finally:
            self._downloading = False

    def start_download(self, urls, format_choice, playlist_title=None):
        if self._downloading:
            return "Already downloading"
        self._downloading = True
        self._cancel_requested = False
        thread = threading.Thread(target=self._download_thread, args=(urls, format_choice, playlist_title))
        thread.daemon = True
        thread.start()
        return "Started"

    def search_youtube(self, query):
        num_results = 25 if self.settings.get('deep_search') else 10
        ydl_opts = {
            'extract_flat': True,
            'quiet': True,
            'nocheckcertificate': True,
            'socket_timeout': 10
        }
        
        channel_match = None
        # Step 1: Search for matching channel (limit to 1 result for speed)
        import urllib.parse
        try:
            encoded_query = urllib.parse.quote(query)
            channel_search_url = f"https://www.youtube.com/results?search_query={encoded_query}&sp=EgIQAg%253D%253D"
            channel_opts = ydl_opts.copy()
            channel_opts['playlistend'] = 1
            
            with yt_dlp.YoutubeDL(channel_opts) as ydl:
                channel_info = ydl.extract_info(channel_search_url, download=False)
                if channel_info and channel_info.get('entries'):
                    first_channel = channel_info['entries'][0]
                    c_title = first_channel.get('title', '')
                    # Check if query words are in the channel title
                    query_words = query.lower().split()
                    title_lower = c_title.lower()
                    if query.lower() in title_lower or any(word in title_lower for word in query_words):
                        avatar_url = ""
                        if first_channel.get('thumbnails'):
                            avatar_url = first_channel['thumbnails'][-1].get('url') or ""
                        channel_match = {
                            'title': c_title,
                            'url': first_channel.get('url'),
                            'avatar_url': avatar_url
                        }
        except Exception as e:
            print("Channel search error:", e)
            
        # Step 2: Search for regular video results
        search_query = f"ytsearch{num_results}:{query}"
        results = []
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    for entry in info['entries']:
                        results.append({
                            'id': entry.get('id'),
                            'title': entry.get('title'),
                            'url': entry.get('url'),
                            'uploader': entry.get('uploader')
                        })
        except Exception as e:
            print("Search error:", e)
            
        return {
            'channel_match': channel_match,
            'videos': results
        }

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

if __name__ == '__main__':
    api = Api()
    
    html_path = resource_path(os.path.join('frontend', 'index.html'))
    
    window = webview.create_window(
        "YoredTube V5 - כל הזכויות שמורות ל- working.cohen - מתמחיםטופ", 
        url=html_path, 
        js_api=api,
        width=800, 
        height=600,
        resizable=True,
        background_color='#f8f9fa' if api.settings.get('theme') == 'light' else '#131314'
    )
    
    api.set_window(window)
    webview.start()
