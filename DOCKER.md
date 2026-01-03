# 🐳 Docker Deployment Guide

Complete guide for containerizing and deploying the PPE Safety Monitor application using Docker.

---

## 📋 Table of Contents

- [Prerequisites](#prerequisites)
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

## 🚀 Quick Start

### 1. Build Docker Image
```bash
# Basic build (CPU only)
docker build -t ppe-monitor:latest .

# Build with GPU support
docker build -t ppe-monitor:gpu --build-arg CUDA_VERSION=11.8 .
```

### 2. Run Container
```bash
# CPU version
docker run -d \
  --name ppe-monitor \
  -p 5000:5000 \
  -v $(pwd)/violation_data:/app/violation_data \
  -v $(pwd)/Recordings:/app/Recordings \
  ppe-monitor:latest

# GPU version
docker run -d \
  --name ppe-monitor \
  --gpus all \
  -p 5000:5000 \
  -v $(pwd)/violation_data:/app/violation_data \
  -v $(pwd)/Recordings:/app/Recordings \
  ppe-monitor:gpu
```

### 3. Access Application
```bash
# Check logs
docker logs -f ppe-monitor

# Access application
# Open browser: http://localhost:5000
```

---

## 📝 Dockerfile Configuration

### Basic Dockerfile (CPU)

```dockerfile
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
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
ENV QT_QPA_PLATFORM=offscreen

# Run application
CMD ["python", "app.py"]
```

### GPU-Enabled Dockerfile

```dockerfile
FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# Install Python
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
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
ENV QT_QPA_PLATFORM=offscreen
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

CMD ["python3", "app.py"]
```

---

## 🎼 Docker Compose Setup

### docker-compose.yml (CPU)

```yaml
version: '3.8'

services:
  ppe-monitor:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: ppe-monitor
    ports:
      - "5000:5000"
    volumes:
      - ./violation_data:/app/violation_data
      - ./Recordings:/app/Recordings
      - ./Saved_Detections:/app/Saved_Detections
      - ./models:/app/models
    environment:
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - PYTHONUNBUFFERED=1
      - QT_QPA_PLATFORM=offscreen
    env_file:
      - .env
    restart: unless-stopped
    networks:
      - ppe-network

  # Optional: IP Camera simulator
  ipcamera-simulator:
    build:
      context: .
      dockerfile: Dockerfile.ipcamera
    container_name: ipcamera-sim
    ports:
      - "8080:5000"
    volumes:
      - ./test_videos:/app/videos
    restart: unless-stopped
    networks:
      - ppe-network

networks:
  ppe-network:
    driver: bridge

volumes:
  violation_data:
  recordings:
```

### docker-compose.gpu.yml (GPU Support)

```yaml
version: '3.8'

services:
  ppe-monitor:
    build:
      context: .
      dockerfile: Dockerfile.gpu
      args:
        CUDA_VERSION: 11.8
    container_name: ppe-monitor-gpu
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
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_KEY=${SUPABASE_KEY}
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
      - PYTHONUNBUFFERED=1
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

### 3. Build GPU Image
```bash
docker build -f Dockerfile.gpu -t ppe-monitor:gpu .
```

### 4. Run with GPU
```bash
docker run --gpus all \
  -p 5000:5000 \
  -v $(pwd)/violation_data:/app/violation_data \
  ppe-monitor:gpu
```

---

## 🏭 Production Deployment

### Multi-Stage Build

```dockerfile
# Stage 1: Builder
FROM python:3.10-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application
COPY . .

# Security: Create non-root user
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

CMD ["python", "app.py"]
```

### Environment Variables

Create `.env.production`:
```env
# Application
APP_ENV=production
DEBUG=false

# Supabase
SUPABASE_URL=your_production_url
SUPABASE_KEY=your_production_key

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SENDER_EMAIL=alerts@company.com

# Performance
MAX_WORKERS=4
FRAME_BUFFER_SIZE=5
```

### Kubernetes Deployment (Optional)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ppe-monitor
spec:
  replicas: 2
  selector:
    matchLabels:
      app: ppe-monitor
  template:
    metadata:
      labels:
        app: ppe-monitor
    spec:
      containers:
      - name: ppe-monitor
        image: ppe-monitor:latest
        ports:
        - containerPort: 5000
        resources:
          limits:
            nvidia.com/gpu: 1
          requests:
            memory: "4Gi"
            cpu: "2"
        volumeMounts:
        - name: data
          mountPath: /app/violation_data
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: ppe-data-pvc
```

---

## 🛠️ Troubleshooting

### Container Won't Start
```bash
# Check logs
docker logs ppe-monitor

# Inspect container
docker inspect ppe-monitor

# Enter container shell
docker exec -it ppe-monitor /bin/bash
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
docker run -p 5001:5000 ppe-monitor
```

### Volume Permissions
```bash
# Fix permissions on host
sudo chown -R $(id -u):$(id -g) ./violation_data

# Or run container as current user
docker run --user $(id -u):$(id -g) ppe-monitor
```

### Memory Issues
```bash
# Increase Docker memory limit
# Docker Desktop: Settings > Resources > Memory

# Check container memory usage
docker stats ppe-monitor

# Limit container memory
docker run -m 4g ppe-monitor
```

---

## 📊 Monitoring & Logging

### Health Checks

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:5000/health')"
```

### Logging Configuration

```yaml
services:
  ppe-monitor:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring with Prometheus (Optional)

```yaml
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

---

## 🔐 Security Best Practices

1. **Don't include .env in image**
   ```dockerfile
   # Add to .dockerignore
   .env
   .env.local
   *.key
   *.pem
   ```

2. **Use secrets management**
   ```bash
   docker secret create supabase_url supabase_url.txt
   docker secret create supabase_key supabase_key.txt
   ```

3. **Scan images for vulnerabilities**
   ```bash
   docker scan ppe-monitor:latest
   ```

4. **Use multi-stage builds** (shown above)

5. **Run as non-root user** (shown above)

---

## 📚 Additional Resources

- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Reference](https://docs.docker.com/compose/compose-file/)
- [NVIDIA Container Toolkit](https://github.com/NVIDIA/nvidia-docker)
- [Best Practices for Writing Dockerfiles](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/)

---

<div align="center">

**Need help? Open an issue on [GitHub](https://github.com/yourusername/ppe-safety-monitor/issues)**

</div>