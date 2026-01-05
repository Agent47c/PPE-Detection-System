# 🐳 Docker Deployment Guide

Complete guide for containerizing and deploying the PPE Safety Monitor application using Docker with GUI support.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
- [GUI Display Setup (Windows)](#gui-display-setup-windows)
- [Quick Start](#quick-start)
- [Dockerfile Configuration](#dockerfile-configuration)
- [Docker Compose Setup](#docker-compose-setup)
- [GPU Support](#gpu-support)
- [Production Deployment](#production-deployment)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

### Required Software
- **Docker**: 20.10+ ([Install Docker](https://docs.docker.com/get-docker/))
- **Docker Compose**: 2.0+ (included with Docker Desktop)
- **VcXsrv** (Windows): For GUI display support ([Download](https://sourceforge.net/projects/vcxsrv/))
- **NVIDIA Container Toolkit**: For GPU support ([Install Guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html))

### Verify Installation
```bash
# Check Docker
docker --version

# Check Docker Compose
docker compose version

# Check NVIDIA runtime (if using GPU)
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

---

## 🖥️ GUI Display Setup (Windows)

### Step 1: Install VcXsrv

1. **Download VcXsrv**
   - Download from [SourceForge](https://sourceforge.net/projects/vcxsrv/)
   - Run the installer and follow the installation wizard

2. **Launch VcXsrv (XLaunch)**
   - Open **XLaunch** from Start Menu
   - Configure with these settings:

#### XLaunch Configuration:

**Display Settings:**
```
○ Multiple windows
  Display number: 0
```

**Client Startup:**
```
○ Start no client
```

**Extra Settings:**
```
☑ Clipboard
☑ Primary Selection
☑ Native opengl
☑ Disable access control
```

3. **Save Configuration (Optional)**
   - Click "Save configuration" and save as `config.xlaunch`
   - Double-click this file to launch VcXsrv with saved settings

### Step 2: Configure Windows Firewall

Run this PowerShell command as Administrator:

```powershell
New-NetFirewallRule -DisplayName "VcXsrv" -Direction Inbound -Program "C:\Program Files\VcXsrv\vcxsrv.exe" -Action Allow
```

Or manually:
1. Open **Windows Defender Firewall**
2. Click **Allow an app through firewall**
3. Click **Change settings** → **Allow another app**
4. Browse to `C:\Program Files\VcXsrv\vcxsrv.exe`
5. Add and ensure both Private and Public are checked

### Step 3: Verify VcXsrv is Running

Check system tray for VcXsrv icon (X server icon). If not visible, launch XLaunch again.

---

## 🚀 Quick Start
### Using Helper Scripts (Automaticlly Run The Scripts After Setting Up)

**Windows:**
```powershell
.\run-docker.ps1
```

**Linux/Mac:**
```bash
chmod +x run-docker.sh
./run-docker.sh
```
## Manual Setting Up Docker
### 1. Build Docker Image

```bash
# Basic build (CPU with GUI support)
docker build -t ppe-detection-app:latest .

# Build with GPU support
docker build -f Dockerfile.gpu -t ppe-detection-app:gpu .
```

### 2. Run Container with Display Support

#### Windows with VcXsrv:

```bash
docker run -it --rm \
  -e DISPLAY=host.docker.internal:0.0 \
  -p 5000:5000 \
  -v "%cd%/violation_data:/app/violation_data" \
  -v "%cd%/Recordings:/app/Recordings" \
  ppe-detection-app
```

#### Windows PowerShell:

```powershell
docker run -it --rm `
  -e DISPLAY=host.docker.internal:0.0 `
  -p 5000:5000 `
  -v "${PWD}/violation_data:/app/violation_data" `
  -v "${PWD}/Recordings:/app/Recordings" `
  ppe-detection-app
```

#### Linux with X11:

```bash
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -p 5000:5000 \
  -v $(pwd)/violation_data:/app/violation_data \
  -v $(pwd)/Recordings:/app/Recordings \
  ppe-detection-app
```

#### With GPU Support:

```bash
docker run -it --rm \
  --gpus all \
  -e DISPLAY=host.docker.internal:0.0 \
  -p 5000:5000 \
  -v "%cd%/violation_data:/app/violation_data" \
  -v "%cd%/Recordings:/app/Recordings" \
  ppe-detection-app:gpu
```

### 3. Access Application

```bash
# Application will display GUI windows via VcXsrv
# Web interface: http://localhost:5000
```

---

## 📝 Dockerfile Configuration

### Basic Dockerfile (CPU with GUI Support)

```dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies including X11
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libx11-6 \
    libxcb1 \
    libxau6 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create directories
RUN mkdir -p violation_data Recordings Saved_Detections

# Expose port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=xcb
ENV QT_X11_NO_MITSHM=1

# Run application
CMD ["python", "app.py"]
```

### GPU-Enabled Dockerfile

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python and X11 dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libx11-6 \
    libxcb1 \
    libxau6 \
    wget \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Install PyTorch with CUDA support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Copy application
COPY . .

# Create directories
RUN mkdir -p violation_data Recordings Saved_Detections

EXPOSE 5000

ENV PYTHONUNBUFFERED=1
ENV QT_QPA_PLATFORM=xcb
ENV QT_X11_NO_MITSHM=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

CMD ["python3", "app.py"]
```

---

## 🎼 Docker Compose Setup

### docker-compose.yml (CPU with Display)

```yaml
version: '3.8'

services:
  ppe-monitor:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ppe-detection-app
    stdin_open: true
    tty: true
    ports:
      - "5000:5000"
    volumes:
      - ./violation_data:/app/violation_data
      - ./Recordings:/app/Recordings
      - ./Saved_Detections:/app/Saved_Detections
      - ./models:/app/models
    environment:
      - DISPLAY=host.docker.internal:0.0
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - PYTHONUNBUFFERED=1
      - QT_QPA_PLATFORM=xcb
      - QT_X11_NO_MITSHM=1
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - ppe-network

networks:
  ppe-network:
    driver: bridge
```

### docker-compose.gpu.yml (GPU + Display Support)

```yaml
version: '3.8'

services:
  ppe-monitor:
    build:
      context: .
      dockerfile: Dockerfile.gpu
      args:
        CUDA_VERSION: 11.8
    container_name: ppe-detection-app-gpu
    stdin_open: true
    tty: true
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    ports:
      - "5000:5000"
    volumes:
      - ./violation_data:/app/violation_data
      - ./Recordings:/app/Recordings
      - ./Saved_Detections:/app/Saved_Detections
      - ./models:/app/models
    environment:
      - DISPLAY=host.docker.internal:0.0
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - PYTHONUNBUFFERED=1
      - QT_QPA_PLATFORM=xcb
      - QT_X11_NO_MITSHM=1
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - ppe-network

networks:
  ppe-network:
    driver: bridge
```

### Usage

```bash
# Start services (CPU)
docker compose up -d

# Start services (GPU)
docker compose -f docker-compose.gpu.yml up -d

# View logs
docker compose logs -f

# Stop services
docker compose down

# Rebuild and restart
docker compose up -d --build
```

---

## 🎮 GPU Support

### 1. Install NVIDIA Container Toolkit

#### Ubuntu/Debian
```bash
# Add repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Restart Docker
sudo systemctl restart docker
```

#### Windows (WSL2)
1. Install [NVIDIA CUDA on WSL](https://docs.nvidia.com/cuda/wsl-user-guide/index.html)
2. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/windows/install/)
3. Enable WSL2 integration in Docker Desktop settings

### 2. Verify GPU Access
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

---

## 🛠️ Troubleshooting

### Display Issues

#### Problem: "cannot open display: host.docker.internal:0.0"

**Solution:**
1. Ensure VcXsrv is running (check system tray)
2. Restart VcXsrv with "Disable access control" checked
3. Check Windows Firewall allows VcXsrv

```powershell
# Test VcXsrv connection
docker run -it --rm -e DISPLAY=host.docker.internal:0.0 ubuntu bash
apt-get update && apt-get install -y x11-apps
xclock
```

#### Problem: GUI windows not appearing

**Solution:**
```bash
# In container, test X11 connection
echo $DISPLAY
xdpyinfo

# If fails, verify VcXsrv is running on display :0
```

### Container Won't Start
```bash
# Check logs
docker logs ppe-detection-app

# Inspect container
docker inspect ppe-detection-app

# Enter container shell
docker exec -it ppe-detection-app /bin/bash
```

### GPU Not Detected
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Verify Docker daemon configuration
cat /etc/docker/daemon.json

# Should include:
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}
```

### Port Already in Use
```bash
# Find process using port 5000
lsof -i :5000

# Change port mapping
docker run -p 5001:5000 ppe-detection-app
```

### Volume Permissions
```bash
# Fix permissions on host
sudo chown -R $(id -u):$(id -g) ./violation_data

# Or run container as current user
docker run --user $(id -u):$(id -g) ppe-detection-app
```

---

## 📝 Quick Reference Commands

### Windows Command Prompt
```cmd
REM Build image
docker build -t ppe-detection-app .

REM Run with display
docker run -it --rm -e DISPLAY=host.docker.internal:0.0 -p 5000:5000 -v "%cd%/violation_data:/app/violation_data" -v "%cd%/Recordings:/app/Recordings" ppe-detection-app

REM Run with GPU
docker run -it --rm --gpus all -e DISPLAY=host.docker.internal:0.0 -p 5000:5000 -v "%cd%/violation_data:/app/violation_data" -v "%cd%/Recordings:/app/Recordings" ppe-detection-app:gpu
```

### Windows PowerShell
```powershell
# Build image
docker build -t ppe-detection-app .

# Run with display
docker run -it --rm `
  -e DISPLAY=host.docker.internal:0.0 `
  -p 5000:5000 `
  -v "${PWD}/violation_data:/app/violation_data" `
  -v "${PWD}/Recordings:/app/Recordings" `
  ppe-detection-app

# Run with GPU
docker run -it --rm `
  --gpus all `
  -e DISPLAY=host.docker.internal:0.0 `
  -p 5000:5000 `
  -v "${PWD}/violation_data:/app/violation_data" `
  -v "${PWD}/Recordings:/app/Recordings" `
  ppe-detection-app:gpu
```

### Linux Bash
```bash
# Build image
docker build -t ppe-detection-app .

# Run with display
docker run -it --rm \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -p 5000:5000 \
  -v $(pwd)/violation_data:/app/violation_data \
  -v $(pwd)/Recordings:/app/Recordings \
  ppe-detection-app

# Run with GPU
docker run -it --rm \
  --gpus all \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -p 5000:5000 \
  -v $(pwd)/violation_data:/app/violation_data \
  -v $(pwd)/Recordings:/app/Recordings \
  ppe-detection-app:gpu
```

---

## 🎯 VcXsrv Startup Script

Create `start-vcxsrv.bat` for easy VcXsrv startup:

```batch
@echo off
echo Starting VcXsrv X Server...
start "" "C:\Program Files\VcXsrv\vcxsrv.exe" :0 -ac -terminate -lesspointer -multiwindow -clipboard -wgl -dpi auto

echo Waiting for X Server to start...
timeout /t 3 /nobreak > nul

echo VcXsrv started successfully!
echo You can now run Docker containers with GUI support.
pause
```

Or PowerShell version `start-vcxsrv.ps1`:

```powershell
Write-Host "Starting VcXsrv X Server..." -ForegroundColor Green
Start-Process "C:\Program Files\VcXsrv\vcxsrv.exe" -ArgumentList ":0", "-ac", "-terminate", "-lesspointer", "-multiwindow", "-clipboard", "-wgl", "-dpi", "auto"

Start-Sleep -Seconds 3
Write-Host "VcXsrv started successfully!" -ForegroundColor Green
Write-Host "You can now run Docker containers with GUI support." -ForegroundColor Cyan
```

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [VcXsrv Documentation](https://sourceforge.net/projects/vcxsrv/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [X11 Forwarding Guide](https://wiki.archlinux.org/title/OpenSSH#X11_forwarding)

---

<div align="center">

**Need help? Open an issue on [GitHub](https://github.com/yourusername/ppe-safety-monitor/issues)**

</div>