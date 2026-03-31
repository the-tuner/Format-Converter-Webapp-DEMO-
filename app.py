import os
from pathlib import Path
from contextlib import contextmanager
from flask import Flask, request, send_file, jsonify
from werkzeug.utils import secure_filename
from PIL import Image
from moviepy import VideoFileClip, AudioFileClip 
import pypandoc
# for pdf
from pdfminer.high_level import extract_text 

app = Flask(__name__, 
            static_folder='assets', 
            static_url_path='/assets', 
            template_folder='.')

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / "temp_uploads"
UPLOAD_FOLDER.mkdir(exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB 

@contextmanager
def temp_file(path):
    try:
        yield path
    finally:
        if path.exists():
            try:
                path.unlink()
            except Exception:
                pass

@app.route('/')
def index():
    return send_file(BASE_DIR / 'index.html')

@app.route('/main.css')
def styles():
    return send_file(BASE_DIR / 'main.css')

@app.route('/convert', methods=['POST'])
def convert_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    target_ext = request.form.get('target', '').lower().strip()
    filename = secure_filename(file.filename)
    input_path = UPLOAD_FOLDER / filename

    file.seek(0, os.SEEK_END)
    if file.tell() > MAX_FILE_SIZE:
        return jsonify({"error": "File too large"}), 413
    file.seek(0)

    try:
        file.save(input_path)
        output_filename = f"{input_path.stem}.{target_ext}"
        output_path = UPLOAD_FOLDER / output_filename
        ext = input_path.suffix.lstrip('.').lower()

        with temp_file(input_path), temp_file(output_path):
            
            #img
            if ext in {'png', 'jpg', 'jpeg', 'webp'} and target_ext in {'png', 'jpg', 'jpeg', 'webp'}:
                with Image.open(input_path) as img:
                    if target_ext in {'jpg', 'jpeg'} and img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    save_fmt = 'JPEG' if target_ext in {'jpg', 'jpeg'} else target_ext.upper()
                    img.save(output_path, save_fmt)

            #vid
            elif ext in {'mp4', 'mov'} and target_ext in {'mp4', 'mov'}:
                with VideoFileClip(str(input_path)) as clip:
                    clip.write_videofile(str(output_path), codec='libx264', audio_codec='aac', logger=None)

            #audio xtract
            elif ext in {'mp4', 'mov'} and target_ext in {'mp3', 'wav', 'aac'}:
                with VideoFileClip(str(input_path)) as clip:
                    if clip.audio is None:
                        return jsonify({"error": "This video file has no audio track"}), 400
                    clip.audio.write_audiofile(str(output_path), logger=None)

            #audio
            elif ext in {'mp3', 'wav', 'aac'} and target_ext in {'mp3', 'wav', 'aac'}:
                with AudioFileClip(str(input_path)) as clip:
                    clip.write_audiofile(str(output_path), logger=None)

            #text
            elif ext in {'txt', 'docx', 'pdf'} and target_ext in {'txt', 'docx', 'pdf'}:
                if ext == 'pdf':
                    # Manually extract text because Pandoc cannot 'read' PDF 
                    text_content = extract_text(str(input_path))
                    if target_ext == 'txt':
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(text_content)
                    else:
                        pypandoc.convert_text(text_content, 'docx', format='md', outputfile=str(output_path))
                else:
                    from_fmt = 'markdown' if ext == 'txt' else 'docx'
                    extra_args = ['--pdf-engine=xelatex'] if target_ext == 'pdf' else []
                    pypandoc.convert_file(str(input_path), target_ext, format=from_fmt, 
                                          outputfile=str(output_path), extra_args=extra_args)

            else:
                return jsonify({"error": f"Conversion from {ext} to {target_ext} is not supported"}), 400

            return send_file(output_path, as_attachment=True, download_name=f"converted_{output_filename}")

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)