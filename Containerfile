FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    pandoc \
    texlive-latex-base \
    texlive-fonts-recommended \
    texlive-xetex \
    lmodern \
    fonts-noto-cjk \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -m appuser && mkdir -p /app/temp_uploads

COPY . .

RUN chmod -R 777 /app && chown -R appuser:appuser /app

USER appuser

EXPOSE 5000

CMD ["python3", "app.py"]