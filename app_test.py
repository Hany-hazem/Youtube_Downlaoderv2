from flask import Flask, render_template, request, redirect, url_for
import os
from yt_dlp import YoutubeDL
import subprocess
from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, error
import requests
from io import BytesIO
from PIL import Image
import shutil

app = Flask(__name__)

class Downloader:
    def __init__(self, download_path):
        self.download_path = download_path
        self.temp_download_path = os.path.join(download_path, 'Temp')
        self.final_download_path = os.path.join(download_path, 'Downloaded')
        os.makedirs(self.temp_download_path, exist_ok=True)
        os.makedirs(self.final_download_path, exist_ok=True)

    def download_video(self, yt_url, resolution):
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]' if resolution == 'high' else 'worst',
            'outtmpl': os.path.join(self.temp_download_path, '%(title)s.%(ext)s'),
        }
        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([yt_url])

    def download_audio(self, yt_url, file_format):
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': file_format,
                'preferredquality': '320',
            }],
            'outtmpl': os.path.join(self.temp_download_path, '%(title)s.%(ext)s'),
            'writethumbnail': True,
        }
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(yt_url, download=True)
            file_path = ydl.prepare_filename(info_dict)
            new_file_name = info_dict.get('title', 'NewAudioFile') + '.' + file_format
            new_file_path = os.path.join(self.download_path, new_file_name)
            if not os.path.exists(new_file_path):
                os.rename(file_path, new_file_path)
                print(f"File renamed to {new_file_name}")
            else:
                print(f"File {new_file_name} already exists. Choose a different name or remove the existing file.")
            file_path = new_file_path
            if file_format != 'mp3':
                new_file_path = file_path.rsplit('.', 1)[0] + '.mp3'
                if subprocess.run(['ffmpeg', '-i', file_path, new_file_path]).returncode == 0:
                    print("Conversion successful.")
                    file_path = new_file_path
                else:
                    print("Conversion failed.")
            if os.path.exists(file_path):
                try:
                    audio_file = EasyID3(new_file_path)
                    audio_file['title'] = info_dict.get('title', '')
                    audio_file['artist'] = info_dict.get('uploader', '')
                    audio_file['album'] = info_dict.get('uploader', '')
                    audio_file['date'] = str(info_dict.get('upload_date', ''))[:4]
                    audio_file.save()
                except Exception as e:
                    print(f"Failed to embed metadata: {e}")
                self.embed_thumbnail(file_path, info_dict.get('thumbnail', ''))
                final_file_path = os.path.join(self.final_download_path, os.path.basename(file_path))
                shutil.move(file_path, final_file_path)
                print(f"File moved to {final_file_path}")

    def embed_thumbnail(self, audio_file_path, thumbnail_url):
        if thumbnail_url:
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                image = Image.open(image_data)
                if image.format != 'JPEG':
                    image = image.convert('RGB')
                audio = ID3(audio_file_path)
                mime_type = 'image/jpeg' if thumbnail_url.endswith('.jpg') else 'image/webp'
                audio.add(APIC(mime=mime_type, type=3, desc='Cover', data=image_data.getvalue()))
                audio.save()
                print("Thumbnail embedded successfully.")
            else:
                print("Failed to download thumbnail.")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['videoURL']
        download_type = request.form['downloadType']
        file_format = request.form.get('fileFormat', 'mp3')
        resolution = request.form.get('resolution', 'high')
        downloader = Downloader(os.path.dirname(os.path.abspath(__file__)))
        if download_type == 'video':
            downloader.download_video(video_url, resolution)
        elif download_type == 'audio':
            downloader.download_audio(video_url, file_format)
        return redirect(url_for('download_complete'))
    return render_template('index.html')

@app.route('/download_complete')
def download_complete():
    return '''Download Complete! <br><br> <a href="/">Start another download</a>'''

if __name__ == '__main__':
    app.run(debug=True)
