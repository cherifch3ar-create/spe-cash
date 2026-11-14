#!/bin/bash
# Installation du robot WhatsApp Web SPE sur Ubuntu 22.04 (Oracle Always Free ou mini-PC). Lancer en utilisateur normal.
set -e
sudo apt-get update -qq && sudo apt-get install -y -qq git curl chromium-browser fonts-liberation libnss3 libatk-bridge2.0-0 libgbm1 libasound2 >/dev/null
if ! command -v node >/dev/null; then curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt-get install -y nodejs; fi
cd "$HOME" && if [ -d spe-cash ]; then (cd spe-cash && git pull -q); else git clone -q https://github.com/cherifch3ar-create/spe-cash.git; fi
cd spe-cash/robots/whatsapp_web && npm install --omit=dev
sudo tee /etc/systemd/system/spe-whatsapp.service >/dev/null <<UNIT
[Unit]
Description=Robot WhatsApp Web SPE
After=network-online.target
[Service]
WorkingDirectory=$HOME/spe-cash/robots/whatsapp_web
ExecStart=$(command -v node) index.js
Restart=always
RestartSec=30
User=$USER
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload && sudo systemctl enable spe-whatsapp
echo "Installé. Premier lancement pour scanner le QR : cd ~/spe-cash/robots/whatsapp_web && npm start ; puis : sudo systemctl start spe-whatsapp"
