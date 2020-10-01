cp nginx.conf /etc/nginx/

mkdir -p /usr/bin/horizontal_scaler
cp server.py /usr/bin/horizontal_scaler/
cp config.json /usr/bin/horizontal_scaler/
chmod +x /usr/bin/horizontal_scaler/server.py

cp horizontal_scaler.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable horizontal_scaler.service