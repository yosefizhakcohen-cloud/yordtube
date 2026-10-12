import urllib.request
import zipfile
import os

url = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
zip_path = "ffmpeg.zip"

print("Downloading ffmpeg...")
urllib.request.urlretrieve(url, zip_path)
print("Downloaded. Extracting...")

with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    for file in zip_ref.namelist():
        if file.endswith('ffmpeg.exe') or file.endswith('ffprobe.exe'):
            zip_ref.extract(file, '.')
            # move to current dir
            base_file = os.path.basename(file)
            os.rename(file, base_file)

print("Done. Cleaning up...")
os.remove(zip_path)
# clean up extracted dir if empty
import shutil
for d in os.listdir('.'):
    if os.path.isdir(d) and d.startswith('ffmpeg-master'):
        shutil.rmtree(d)
