sudo mkdir -p /var/www/horizontal_scaler
sudo cp index.php /var/www/horizontal_scaler

ufw allow 3337/tcp

sudo cp horizontal_scaler.conf /etc/apache2/sites-available
sudo a2ensite horizontal_scaler.conf
systemctl reload apache2
