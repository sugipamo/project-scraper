FROM selenium/standalone-chrome:latest

USER root

# curlのインストール
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

USER seluser 