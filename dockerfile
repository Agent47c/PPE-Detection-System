# Use Python 3.11 slim image as base
FROM python:3.11-slim

# Set working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libqt5gui5 \
    libqt5core5a \
    libqt5widgets5 \
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xfixes0 \
    libxkbcommon-x11-0 \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*


# Set environment variables for Qt
ENV QT_QPA_PLATFORM=xcb
ENV DISPLAY=:0
ENV QT_X11_NO_MITSHM=1

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# Copy application files
COPY app.py .
COPY auth_manager.py .
COPY objecttracking.py .
COPY PPE.png .
COPY .env .

# Create directories for models and data
RUN mkdir -p yolo_models tracking_models Saved_Detections violation_data Recordings
# CRITICAL FIX: Delete the conflicting Qt plugins bundled with OpenCV
# This forces PyQt5 to use its own correct plugins
RUN rm -rf /usr/local/lib/python3.11/site-packages/cv2/qt

# Copy model files (if they exist locally)
# Create directories

# Copy models from host → image
COPY yolo_models/ yolo_models/
COPY tracking_models/ tracking_models/



# Set permissions
RUN chmod +x app.py


# Run the application
CMD ["python", "app.py"]