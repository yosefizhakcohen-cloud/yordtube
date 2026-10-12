from PIL import Image

img = Image.open(r"C:\Users\adaly\.gemini\antigravity\brain\79acf945-36b5-469f-8232-e62429536405\yoredtube_icon_1781817048276.png")
icon_sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
img.save(r"C:\Users\adaly\.gemini\antigravity\scratch\youtube-downloader\app_icon.ico", format="ICO", sizes=icon_sizes)
print("Icon converted successfully.")
