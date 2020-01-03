cp horizontal_scaler.service /etc/systemd/system/
cp load-balancer.conf /etc/nginx/conf.d/
mkdir -p /usr/bin/horizontal_scaler
cp server.py /usr/bin/horizontal_scaler/
cp config.json /usr/bin/horizontal_scaler/