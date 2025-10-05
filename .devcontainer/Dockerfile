# Pythonの公式イメージ
FROM python:3.9-slim

# 作業ディレクトリ
WORKDIR /usr/src/app

# 依存パッケージ・Chromium・日本語フォントをインストール
RUN apt-get update && apt-get install -y --no-install-recommends \
    git build-essential curl ca-certificates wget gnupg \
    # Chromium（Puppeteerの実行本体として使用）
    chromium \
    # 日本語フォント（PDFで豆腐対策）
    fonts-noto-cjk fonts-ipafont-mincho fonts-ipafont-gothic fonts-noto-color-emoji \
    # Puppeteer/Chromium の依存
    libasound2 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 libxkbcommon0 \
    libgbm1 libgtk-3-0 libnspr4 libnss3 libxss1 libxcomposite1 libxdamage1 \
    libxrandr2 libxshmfence1 libx11-xcb1 libxtst6 libxfixes3 libpango-1.0-0 \
    libpangocairo-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Node.js LTS を導入（NodeSource）
RUN curl -fsSL https://deb.nodesource.com/setup_lts.x | bash - \
    && apt-get update && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# PuppeteerがChromiumを再ダウンロードしないように設定
ENV PUPPETEER_SKIP_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium

# Node.js パッケージをインストール（prettier + puppeteer）
RUN npm install -g prettier \
    && npm install puppeteer

COPY requirements.txt .
RUN pip install -r requirements.txt

# リモートデバッグ用ユーザー（非rootでChromeサンドボックス問題を回避しやすい）
RUN useradd -ms /bin/bash vscode
USER vscode

# ポート開放（Web/Live Server/Nodeデバッグなど）
EXPOSE 3000 8000 5500 9229

# デフォルト
CMD ["/bin/bash"]
