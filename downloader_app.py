import os
import threading
import sys
import customtkinter as ctk
import yt_dlp

# Set the appearance mode and default color theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

# Configure custom fonts
FONT_MAIN = ("Segoe UI", 24, "bold")
FONT_INPUT = ("Segoe UI", 16)
FONT_BTN = ("Segoe UI", 18, "bold")
FONT_STATUS = ("Segoe UI", 14)

class YouTubeDownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("מוריד היוטיוב")
        self.geometry("650x400")
        self.resizable(False, False)

        import os
        import sys
        # Get absolute path to resource, works for dev and for PyInstaller
        def resource_path(relative_path):
            try:
                base_path = sys._MEIPASS
            except Exception:
                base_path = os.path.abspath(".")
            return os.path.join(base_path, relative_path)

        icon_path = resource_path("app_icon.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)
        
        # Main frame with a bit of a custom color
        self.main_frame = ctk.CTkFrame(self, fg_color="#1E1E1E", corner_radius=15)
        self.main_frame.pack(pady=20, padx=20, fill="both", expand=True)

        # Title Label
        self.title_label = ctk.CTkLabel(self.main_frame, text="הורדת תכנים מיוטיוב", font=FONT_MAIN, text_color="#FF0000")
        self.title_label.pack(pady=(20, 20))

        # URL Input
        # justify='right' for Hebrew, but tk entry might just rely on OS for right-to-left
        self.url_entry = ctk.CTkEntry(self.main_frame, placeholder_text="...הדבק כאן את הקישור מיוטיוב", width=500, height=45, font=FONT_INPUT, justify="right")
        self.url_entry.pack(pady=(0, 25))

        # Format Selection (Radio Buttons)
        self.format_var = ctk.StringVar(value="mp4")
        self.radio_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.radio_frame.pack(pady=(0, 25))

        # We place them right-to-left by packing them to the right
        self.radio_mp4 = ctk.CTkRadioButton(self.radio_frame, text="(MP4) וידאו", variable=self.format_var, value="mp4", font=FONT_INPUT, fg_color="#FF0000", hover_color="#CC0000")
        self.radio_mp4.pack(side="right", padx=25)

        self.radio_mp3 = ctk.CTkRadioButton(self.radio_frame, text="(MP3) שמע", variable=self.format_var, value="mp3", font=FONT_INPUT, fg_color="#FF0000", hover_color="#CC0000")
        self.radio_mp3.pack(side="right", padx=25)

        # Download Button
        self.download_button = ctk.CTkButton(self.main_frame, text="הורד עכשיו", command=self.start_download, width=220, height=45, font=FONT_BTN, fg_color="#FF0000", hover_color="#CC0000", text_color="white", corner_radius=8)
        self.download_button.pack(pady=(0, 20))

        # Progress Bar
        self.progress_bar = ctk.CTkProgressBar(self.main_frame, width=500, progress_color="#FF0000")
        self.progress_bar.set(0)
        self.progress_bar.pack(pady=(0, 15))
        self.progress_bar.pack_forget() # Hide initially

        # Status Label
        self.status_label = ctk.CTkLabel(self.main_frame, text="", font=FONT_STATUS, text_color="#AAAAAA")
        self.status_label.pack()

    def update_status(self, text, color="#AAAAAA"):
        self.status_label.configure(text=text, text_color=color)

    def progress_hook(self, d):
        if d['status'] == 'downloading':
            try:
                # Calculate progress percentage
                percent_str = d.get('_percent_str', '0%').strip()
                import re
                percent_str = re.sub(r'\x1b\[[0-9;]*m', '', percent_str)
                percent = float(percent_str.replace('%', '')) / 100.0
                self.progress_bar.set(percent)
                self.update_status(f"...מוריד {percent_str}", "white")
            except Exception as e:
                pass
        elif d['status'] == 'finished':
            self.progress_bar.set(1.0)
            self.update_status("!ההורדה הסתיימה, מעבד את הקובץ", "#00FF00")

    def download_thread(self, url, format_choice):
        # Set download directory to user's Music folder
        music_dir = os.path.join(os.path.expanduser('~'), 'Music')
        if not os.path.exists(music_dir):
            os.makedirs(music_dir)

        ydl_opts = {
            'outtmpl': os.path.join(music_dir, '%(title)s.%(ext)s'),
            'progress_hooks': [self.progress_hook],
            'noplaylist': True,
            'quiet': True,
        }

        if format_choice == 'mp3':
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })
        else: # mp4
            ydl_opts.update({
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            })

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            self.update_status(f"!הקובץ נשמר בהצלחה בתיקיית המוזיקה שלך", "#00FF00")
        except Exception as e:
            self.update_status(f"שגיאה בהורדה, בדוק את הקישור", "#FF0000")
        finally:
            self.download_button.configure(state="normal", text="הורד עכשיו")
            # Hide progress bar after 4 seconds
            self.after(4000, self.progress_bar.pack_forget)

    def start_download(self):
        url = self.url_entry.get().strip()
        if not url:
            self.update_status(".נא להזין קישור תקין מיוטיוב", "#FF0000")
            return

        format_choice = self.format_var.get()
        
        self.download_button.configure(state="disabled", text="...מוריד")
        self.progress_bar.pack(pady=(0, 15))
        self.progress_bar.set(0)
        self.update_status("...מתחיל בהורדה", "white")

        # Run download in a separate thread
        thread = threading.Thread(target=self.download_thread, args=(url, format_choice))
        thread.daemon = True
        thread.start()

if __name__ == "__main__":
    app = YouTubeDownloaderApp()
    app.mainloop()
