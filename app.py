from mutagen.easyid3 import EasyID3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TRCK, TALB, TYER, COMM
import requests
from io import BytesIO
from flask import Flask, render_template, request, redirect, url_for
import os
from yt_dlp import YoutubeDL
import subprocess
from mutagen.id3 import ID3, APIC, error
from mutagen.easyid3 import EasyID3
import requests
from io import BytesIO
from mutagen.id3 import ID3, APIC, error
from mutagen.easyid3 import EasyID3
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
        os.makedirs(self.temp_download_path, exist_ok=True)  # Ensure Temp directory exists
        os.makedirs(self.final_download_path, exist_ok=True)  # Ensure Downloaded directory exists


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
            'writethumbnail': True,  # Download thumbnail for embedding
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

                # Update any references to file_path if further processing is needed
                file_path = new_file_path

            # Convert file format if necessary (e.g., webm to mp3)
            if file_format != 'mp3':
                new_file_path = file_path.rsplit('.', 1)[0] + '.mp3'
                if subprocess.run(['ffmpeg', '-i', file_path, new_file_path]).returncode == 0:
                    print("Conversion successful.")
                    file_path = new_file_path  # Update file_path to the new file
                else:
                    print("Conversion failed.")
            # Check if the file exists before attempting to access it
            if os.path.exists(file_path):

                # Embedding metadata
                try:
                    audio_file = EasyID3(new_file_path)
                    audio_file['title'] = info_dict.get('title', '')
                    audio_file['artist'] = info_dict.get('uploader', '')
                    audio_file['album'] = info_dict.get('uploader', '')
                    audio_file['date'] = str(info_dict.get('upload_date', ''))[:4]  # Extracting year
                    audio_file.save()
                except Exception as e:
                    print(f"Failed to embed metadata: {e}")
                
            else:
                print(f"File does not exist: {file_path}")
        
            thumbnail_url = info_dict['thumbnail']
            desired_thumbnail_path = os.path.join('path_to_save_thumbnail', 'desired_thumbnail_name.jpg')  # Example path and name

            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                image_data = BytesIO(response.content)
                image = Image.open(image_data)
        
            # If the image is not in JPEG format (e.g., WEBP), convert it to JPEG
            if image.format != 'JPEG':
                image = image.convert('RGB')
            
                # Save the image with the desired name
                image.save(desired_thumbnail_path, format='JPEG')
                print(f"Thumbnail saved as {desired_thumbnail_path}")
            else:
                print("Failed to download thumbnail.")

            # Embedding thumbnail
            if 'thumbnail' in info_dict:
                thumbnail_url = info_dict['thumbnail']
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    image_data = BytesIO(response.content)
                    audio = ID3(new_file_path)
                    # Adjust MIME type based on the thumbnail format (JPEG or WEBP)
                    mime_type = 'image/jpeg' if thumbnail_url.endswith('.jpg') else 'image/webp'
                    audio.add(APIC(mime=mime_type, type=3, desc=u'Cover', data=image_data.getvalue()))
                    audio.save()
                else:
                    print("Failed to download thumbnail.")
            

        
            # Embedding thumbnail
            if 'thumbnail' in info_dict:
                thumbnail_url = info_dict['thumbnail']
                response = requests.get(thumbnail_url)
                if response.status_code == 200:
                    image_data = BytesIO(response.content)
                    audio = ID3(new_file_path)
                    # Adjust MIME type based on the thumbnail format (JPEG or WEBP)
                    mime_type = 'image/jpeg' if thumbnail_url.endswith('.jpg') else 'image/webp'
                    audio.add(APIC(mime=mime_type, type=3, desc=u'Cover', data=image_data.getvalue()))
                    audio.save()
                    # After successfully embedding the thumbnail, delete the thumbnail file
                    # os.remove(desired_thumbnail_path)
                else:
                    print("Failed to download thumbnail.")
            # After processing, move file to the Downloaded folder
            final_file_path = os.path.join(self.final_download_path, os.path.basename(file_path))
            shutil.move(file_path, final_file_path)
            print(f"File moved to {final_file_path}")

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        video_url = request.form['videoURL']
        download_type = request.form['downloadType']
        file_format = request.form.get('fileFormat', 'mp3')  # Default to mp3 if not specified
        resolution = request.form.get('resolution', 'high')  # Default to high if not specified
        
        downloader = Downloader(os.path.dirname(os.path.abspath(__file__)))
        if download_type == 'video':
            downloader.download_video(video_url, resolution)
        elif download_type == 'audio':
            downloader.download_audio(video_url, file_format)
        
        return redirect(url_for('download_complete'))
    return render_template('index.html')

@app.route('/download_complete')
def download_complete():
    # Return a message and a link to start another download
    return '''
    Download Complete! <br><br>
    <a href="/">Start another download</a>
    '''

if __name__ == '__main__':
    app.run(debug=True)
    downloader = Downloader(os.path.dirname(os.path.abspath(__file__)))
    downloader.download_audio("youtube_url", "mp3")
    