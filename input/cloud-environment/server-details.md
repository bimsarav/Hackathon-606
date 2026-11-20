Public IP
92.5.154.198

Private IP
172.31.76.23

SSH user
opc

Open ports
These ports are already open on your server. Expose your apps through them; other ports can't be reached from outside.

22 -SSH
80 -HTTP
443 -HTTPS
8080 -Web app or API
8888 -Web app or API
5432 -PostgreSQL

All TCP. Your demo link should use one of these ports, for example
http://92.5.154.198:8080.

Keep your apps running after a reboot
Your server can restart at any time, and judges will open your demo after the deadline. Make sure your apps start again by themselves:

Docker: start containers with --restart unless-stopped (or restart: unless-stopped in Compose), and run sudo systemctl enable docker.
Without Docker: run each app as a systemd service and enable it with sudo systemctl enable --now <your-app>.
Check it: run sudo reboot, wait a minute, then open your demo link again.

Connect
After downloading the key, run these in a terminal (macOS, Linux, or Windows with OpenSSH).
mkdir -p keys && mv ~/Downloads/hackathon22_172.31.76.23 keys/
chmod 600 keys/hackathon22_172.31.76.23
ssh -l opc 92.5.154.198 -i keys/hackathon22_172.31.76.23 -o 'IdentitiesOnly=yes'