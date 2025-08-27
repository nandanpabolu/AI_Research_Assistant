# 🚀 Deployment Guide

This guide covers deploying the AI Research Assistant to various platforms.

## 📋 Prerequisites

- Python 3.8+ installed
- Git repository set up
- All dependencies installed (`pip install -r requirements.txt`)

## 🏠 Local Deployment

### Basic Local Run
```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the application
streamlit run app.py
```

### Production Local Run
```bash
# Run on all network interfaces
streamlit run app.py --server.port 8501 --server.address 0.0.0.0

# Run with specific port
streamlit run app.py --server.port 8503
```

## 🐳 Docker Deployment

### Build and Run
```bash
# Build the image
docker build -t ai-research-assistant .

# Run the container
docker run -p 8501:8501 ai-research-assistant
```

### Using Docker Compose
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## ☁️ Streamlit Cloud Deployment

### 1. Push to GitHub
```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 2. Connect to Streamlit Cloud
1. Go to [share.streamlit.io](https://share.streamlit.io/)
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set main file path: `app.py`
6. Click "Deploy!"

### 3. Configure Environment Variables (Optional)
In Streamlit Cloud settings, you can add:
- `STREAMLIT_SERVER_PORT`: Port number
- `STREAMLIT_SERVER_ADDRESS`: Server address

## 🐙 GitHub Actions Deployment

The repository includes a CI/CD pipeline that:
- Runs tests on multiple Python versions
- Checks code quality (linting, formatting)
- Builds Docker images
- Prepares for deployment

### Manual Trigger
```bash
# Push to trigger CI/CD
git push origin main

# Or create a release tag
git tag v1.0.0
git push origin v1.0.0
```

## 🌐 VPS/Server Deployment

### Using Systemd Service
1. **Create service file** `/etc/systemd/system/ai-research-assistant.service`:
```ini
[Unit]
Description=AI Research Assistant
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/streamlit run app.py --server.port 8501 --server.address 0.0.0.0
Restart=always

[Install]
WantedBy=multi-user.target
```

2. **Enable and start the service**:
```bash
sudo systemctl enable ai-research-assistant
sudo systemctl start ai-research-assistant
sudo systemctl status ai-research-assistant
```

### Using Nginx Reverse Proxy
1. **Install Nginx**:
```bash
sudo apt update
sudo apt install nginx
```

2. **Create Nginx configuration** `/etc/nginx/sites-available/ai-research-assistant`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
```

3. **Enable the site**:
```bash
sudo ln -s /etc/nginx/sites-available/ai-research-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 🔒 Security Considerations

### Firewall Configuration
```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw enable
```

### SSL/HTTPS Setup
```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## 📊 Monitoring and Logs

### View Application Logs
```bash
# Streamlit logs
tail -f ~/.streamlit/logs/streamlit.log

# System logs
sudo journalctl -u ai-research-assistant -f

# Docker logs
docker logs -f ai-research-assistant
```

### Health Checks
```bash
# Check if app is responding
curl http://localhost:8501/_stcore/health

# Check system resources
htop
df -h
free -h
```

## 🚨 Troubleshooting

### Common Issues

1. **Port already in use**:
```bash
# Find process using port
sudo lsof -i :8501

# Kill process
sudo kill -9 <PID>
```

2. **Permission denied**:
```bash
# Fix file permissions
chmod +x app.py
chown -R your-username:your-username /path/to/your/app
```

3. **Dependencies missing**:
```bash
# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### Performance Optimization

1. **Increase Streamlit memory**:
```bash
export STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
export STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200
```

2. **Use production mode**:
```bash
streamlit run app.py --server.headless true --server.enableCORS false
```

## 📈 Scaling Considerations

- **Load Balancing**: Use multiple instances behind a load balancer
- **Caching**: Implement Redis for session storage
- **Database**: Consider PostgreSQL for production use
- **Monitoring**: Use Prometheus + Grafana for metrics

## 🔄 Updates and Maintenance

### Rolling Updates
```bash
# Pull latest changes
git pull origin main

# Restart service
sudo systemctl restart ai-research-assistant

# Or restart Docker container
docker-compose restart
```

### Backup Strategy
```bash
# Backup database
cp data/research.db backup/research_$(date +%Y%m%d_%H%M%S).db

# Backup configuration
cp -r core/ backup/config_$(date +%Y%m%d_%H%M%S)/
```

---

For more help, check the [GitHub Issues](https://github.com/yourusername/ai-research-assistant/issues) or create a new one.



