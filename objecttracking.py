import cv2
import time
import numpy as np
from ultralytics import YOLO
from pathlib import Path
import os
import sys
import os
from boxmot import StrongSort
import queue
import datetime
import threading
import time
from collections import defaultdict
import warnings
import torch

# Fix for NumPy deprecation
if not hasattr(np, 'float'):
    np.float = float
if not hasattr(np, 'int'):
    np.int = int

class VideoLoader:
    def __init__(self, source,log_callback=None):
        self.log_callback=log_callback
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise IOError(f"❌ Could not open video source: {source}")
        
        self.is_live = isinstance(source, int) or str(source).startswith(("rtsp://", "http://"))
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        if not self.fps or self.fps <= 1 or self.fps > 120:
            self.fps = 30
        
        self.frame_interval_ms = int(1000 / self.fps)
        self.last_frame_time = 0
        
        if isinstance(source, int):
            self.send_log(f"Webcam {source} Activated")
        elif str(source).startswith(("http://", "rtsp://")):
            self.send_log(f"IP Camera Connected: {source}")
        else:
            self.send_log(f"Video File Loaded ({self.fps:.2f} FPS)")

    def send_log(self, message, log_type="INFO"):
        """Internal logging method"""
        if self.log_callback:
            try:
                self.log_callback(message, log_type)
            except:
                pass
        
    def read_frame(self):     
        if not self.is_live:
            now = time.time()
            elapsed = (now - self.last_frame_time) * 1000
            
            if elapsed < self.frame_interval_ms:
                time.sleep((self.frame_interval_ms - elapsed) / 1000.0)
            
            self.last_frame_time = time.time()
        
        ret, frame = self.cap.read()
        return ret, frame

    def release(self):
        self.cap.release()

class YOLODetector:
    def __init__(self, Model_path, confidence=0.2,device='cpu',log_callback=None):
        self.log_callback=log_callback
        self.device = device
        self.model = YOLO(Model_path)
        self.model.to(device)  # Move model to device
        self.confidence = confidence
        self.save_enabled = False
        self.output_dir = "Saved/monitor_outputs"
        self.run_name = None
        print("✅ YOLO model loaded")
        self.person_class_ids = [
            class_id for class_id, name in self.model.names.items()
            if name.lower() == "person"
        ]
        self.selected_class_ids = set([0]) 

    def send_log(self, message, log_type="INFO"):
        """Internal logging method"""
        if self.log_callback:
            try:
                self.log_callback(message, log_type)
            except:
                pass

    def update_selected_classes_for_backend(self, class_ids):
        self.selected_class_ids = set(class_ids)
        print(f"🔹 YOLODetector received selected class IDs: {self.selected_class_ids}")
    
    def predict(self, frame):
        return self.model.predict(frame,conf=self.confidence,save=self.save_enabled,project=self.output_dir if self.save_enabled else None,name=self.run_name,classes=list(self.selected_class_ids),verbose=False)

class ObjectTracker:
    def __init__(self,log_callback=None, model_path=None,device='cpu',max_retries=3):
        self.log_callback=log_callback
        
        if model_path is None:
            model_path = Path("osnet_ain_x1_0_market1501_256x128_amsgrad_ep100_lr0.0015_coslr_b64_fb10_softmax_labsmth_flip_jitter.pth")
        else:
            model_path=Path(model_path)
            self.send_log(f"Tracking Model Loaded{model_path}")
        
        self.device = device
        
        warnings.filterwarnings('ignore', message='.*does not have an acceptable suffix.*')
        
        for attempt in range(max_retries):
            try:
                self.tracker = StrongSort(
                    reid_weights=model_path,
                    device=device,
                    half=False
                )
                #self.log_signal.emit(f"StrongSort tracker initialized on {device} With (attempt {attempt + 1})")
                break
            except Exception as e:
                print(f"⚠️ Tracker init attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    print("❌ Failed to initialize tracker after all retries")
                    raise
                time.sleep(0.5)

    def send_log(self, message, log_type="INFO"):
        """Internal logging method"""
        if self.log_callback:
            try:
                self.log_callback(message, log_type)
            except:
                pass

    def track(self, detections, frame):
        return self.tracker.update(detections, frame)

class FPSCounter:
    def __init__(self):
        self.prev_time = time.time()

    def update(self):
        current_time = time.time()
        fps = 1 / (current_time - self.prev_time)
        self.prev_time = current_time
        return fps

class Main_App:
    def __init__(self, Video_path, Model_path,tracking_path, use_gpu, QueueSize,log_callback=None):
        self.log_callback = log_callback
        if use_gpu and torch.cuda.is_available():
            self.device = 'cuda'
            print(f"🚀 Using GPU: {torch.cuda.get_device_name(0)}")
        else:
            self.device = 'cpu'
        print("💻 Using CPU")
        self.Video = VideoLoader(Video_path)
        self.Detector = YOLODetector(Model_path,device=self.device)
        self.Tracker = ObjectTracker(model_path=tracking_path)
        self.FPS_Counter = FPSCounter()
        self.Frame_Count = 0
        self.running = True
        self.frame_queue = queue.Queue(maxsize=QueueSize)
        self.det_queue = queue.Queue(maxsize=QueueSize)
        self.track_queue = queue.Queue(maxsize=QueueSize)
        
        self.Mode = None
        self.mode_lock = threading.Lock()
        
        # Two frame callbacks
        self.frame_callback = None
        self.violation_frame_callback = None
        
        
        self.log_callback = None
        
        # Initialize ViolationDetector
        self.ViolationDetector = ViolationDetector(
            model_names_dict=self.Detector.model.names,
            min_person_confidence=0.8  # Match tracking confidence
        )
        
        # Saving options
        self.save_enabled = False
        self.save_type = "frames"
        self.save_folder = None
        self.video_writer = None
        
        # Frame storage for violation capture
        self.latest_frame = None
        self.latest_violation_frame = None
        self.frame_lock = threading.Lock()
        
        # Keep rate limiting ONLY for MonitorScreen callback (prevents UI overload)
        self._last_frame_callback_time = 0
        self._callback_interval = 1.0 / 30.0
        self.is_full_monitor_mode = False  # Track if we're in Full Monitor
       
        
        print("✅ Main_App initialized with real-time violation detection")
    
    def set_mode(self, mode):
        with self.mode_lock:
            if mode not in ["detection", "tracking", "idle"]:
                print(f"❌ Invalid mode: {mode}")
                return
            
            if mode == "full_monitor":
                self.Mode = "tracking"
                print("🔄 Mode changed to: tracking (full monitor)")
            else:
                self.Mode = mode
                print(f"🔄 Mode changed to: {self.Mode}")
    
    def capture_batch_violation_data(self, violations_list, data_manager):
        """
        Capture multiple violations from the same frame

        Args:
            violations_list: list of violation dicts
            data_manager: ViolationDataManager instance

        Returns:
            batch_id: unique ID for this batch
            cropped_paths: list of cropped image paths
        """
        try:
            frames_acquired = False
            full_frame = None
            violation_frame = None

            # ✅ FIX: More attempts with better diagnostics
            for attempt in range(10):  # Increased from 5 to 10
                try:
                    if self.frame_lock.acquire(blocking=True, timeout=0.3):  # Increased timeout
                        try:
                            # ✅ FIX: Check frames exist with detailed logging
                            has_latest = self.latest_frame is not None
                            has_violation = self.latest_violation_frame is not None

                            if not has_latest:
                                print(f"⚠️ Attempt {attempt+1}: latest_frame is None")
                            if not has_violation:
                                print(f"⚠️ Attempt {attempt+1}: latest_violation_frame is None")

                            if has_latest and has_violation:
                                full_frame = self.latest_frame.copy()
                                violation_frame = self.latest_violation_frame.copy()
                                frames_acquired = True
                                print(f"✅ Frames acquired on attempt {attempt+1}")
                        finally:
                            self.frame_lock.release()

                        if frames_acquired:
                            break
                        else:
                            # ✅ FIX: Wait longer between attempts
                            time.sleep(0.1)
                except Exception as e:
                    print(f"⚠️ Frame lock error (attempt {attempt+1}): {e}")
                    time.sleep(0.1)

            if not frames_acquired:
                print("❌ CRITICAL: Failed to acquire frames after 10 attempts")
                print(f"   latest_frame exists: {self.latest_frame is not None}")
                print(f"   latest_violation_frame exists: {self.latest_violation_frame is not None}")
                return None, []

            # ✅ FIX: Verify frames are valid
            if full_frame is None or violation_frame is None:
                print("❌ CRITICAL: Frames are None after acquisition")
                return None, []

            if not hasattr(full_frame, 'shape') or not hasattr(violation_frame, 'shape'):
                print("❌ CRITICAL: Frames are not valid numpy arrays")
                return None, []

            batch_id, cropped_paths = data_manager.capture_batch_violation(
                violations_list=violations_list,
                full_frame=full_frame,
                detection_frame=violation_frame
            )

            if batch_id:
                print(f"✅ Batch captured: {batch_id} ({len(cropped_paths)} images)")
            else:
                print("❌ data_manager.capture_batch_violation returned None")

            return batch_id, cropped_paths

        except Exception as e:
            print(f"❌ Error capturing batch violation data: {e}")
            import traceback
            traceback.print_exc()
            return None, []
    
    def send_log(self, message, log_type="INFO"):
        """Internal logging method"""
        if self.log_callback:
            try:
                self.log_callback(message, log_type)
            except:
                pass

    def set_violation_classes(self, class_names):
        if not isinstance(class_names, (list, set)):
            print(f"❌ Invalid class names: {class_names}")
            return
        
        self.ViolationDetector.required_classes = set(class_names)
        print(f"✅ Required PPE set: {class_names}")
        self.send_log(f"✅ Required PPE set: {', '.join(class_names)}")

    def enable_violation_detection(self, enabled=True):
        self.ViolationDetector.enabled = enabled
        status = "enabled" if enabled else "disabled"
        print(f"🔔 Violation detection {status}")
        self.send_log(f"🔔 Violation detection {status}")

    def set_violation_callback(self, callback_fn):
        self.ViolationDetector.violation_callback = callback_fn
        print("✅ Violation callback set")

    def set_violation_frame_callback(self, callback_fn):
        self.violation_frame_callback = callback_fn
        print("✅ Violation frame callback set")

    def VideoFrameReader(self):
        while self.running:
            ret, frame = self.Video.read_frame()
            if not ret:
                self.running = False
                self.frame_queue.put(None)
                break
            self.frame_queue.put(frame)
    
    def ObjectDetection(self):
        while self.running:
            try:
                frame = self.frame_queue.get(timeout=1)
            except queue.Empty:
                continue
            if frame is None:
                self.det_queue.put(None)
                break

            with self.mode_lock:
                current_mode = self.Mode

            if current_mode in ["detection", "tracking"]:
                try:
                    results = self.Detector.predict(frame)
                    self.det_queue.put((frame, results))
                except Exception as e:
                    print(f"❌ Detection error: {e}")
                    continue
            else:
                self.det_queue.put((frame, []))

    def ObjectTracking(self):
        while self.running:
            try:
                item = self.det_queue.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                self.track_queue.put(None)
                break

            frame, results = item
            outputs_track = []

            with self.mode_lock:
                current_mode = self.Mode

            if current_mode == "tracking":
                xywh_bboxs, confs, class_ids = [], [], []
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cx, cy = int((x1 + x2)/2), int((y1 + y2)/2)
                        w, h = abs(x2 - x1), abs(y2 - y1)
                        conf = float(box.conf[0])
                        cls = int(box.cls[0])
                        if cls in self.Detector.person_class_ids and conf >= 0.8: # Only track persons with high confidence
                            xywh_bboxs.append([cx, cy, w, h])
                            confs.append(conf)
                            class_ids.append(cls)
                try:
                    detections = []
                    for (cx, cy, w, h), conf, cls in zip(xywh_bboxs, confs, class_ids):
                        x1 = int(cx - w/2)
                        y1 = int(cy - h/2)
                        x2 = int(cx + w/2)
                        y2 = int(cy + h/2)
                        detections.append([x1, y1, x2, y2, conf, cls])
                    detections = np.array(detections)
                    outputs_track = self.Tracker.track(detections, frame)
                except Exception as e:
                    print(f"❌ Tracking error: {e}")
                    outputs_track = []
            else:
                outputs_track = []
            self.track_queue.put((frame, outputs_track, results))
    
    def BoundingBox(self):
        """ Real-time violation frame updates without rate limiting"""
        while self.running:
            try:
                item = self.track_queue.get(timeout=1)
            except queue.Empty:
                continue
            if item is None:
                break

            frame, outputs, results = item
            self.Frame_Count += 1
            fps = self.FPS_Counter.update()

            clean_frame = frame.copy()

            # ✅ FIX: Store clean frame IMMEDIATELY (before violation checking)
            with self.frame_lock:
                self.latest_frame = frame.copy()

            with self.mode_lock:
                current_mode = self.Mode

            if current_mode in ["detection", "tracking"]:
                for result in results:
                    for box in result.boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0])
                        cls = int(box.cls[0])
                        label = self.Detector.model.names.get(cls, f"cls{cls}")

                        if cls in self.Detector.selected_class_ids and cls not in self.Detector.person_class_ids:
                            cv2.rectangle(clean_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                            cv2.putText(clean_frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_PLAIN, 1.5, (0, 255, 0), 2)

                for t in outputs:
                    x1, y1, x2, y2, tid, cls = t[:6].astype(int)
                    cv2.rectangle(clean_frame, (x1, y1), (x2, y2), (225, 200, 0), 2)
                    cv2.putText(clean_frame, f"Person {tid}", (x1, max(0, y1-5)), 
                               cv2.FONT_HERSHEY_PLAIN, 1.5, (255, 200, 0), 3)

            cv2.putText(clean_frame, f"FPS: {int(fps)}", (0, 30), 
                       cv2.FONT_HERSHEY_PLAIN, 2, (0, 225, 0), 5)
            cv2.putText(clean_frame, f"Frame: {self.Frame_Count}", (0, 60), 
                       cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 0), 5)

            violations = []

            if self.ViolationDetector.enabled:
                violations = self.ViolationDetector.check_violations(
                    yolo_results=results,
                    frame_shape=frame.shape[:2]
                )

                if self.violation_frame_callback:
                    violation_frame = frame.copy()

                    persons = []
                    for result in results:
                        for box in result.boxes:
                            cls = int(box.cls[0])
                            if cls in self.Detector.person_class_ids and float(box.conf[0]) >= self.ViolationDetector.min_person_confidence:
                                x1, y1, x2, y2 = map(int, box.xyxy[0])
                                persons.append({
                                    "bbox": (x1, y1, x2, y2),
                                    "confidence": float(box.conf[0])
                                })

                    if violations:
                        violation_frame = self.ViolationDetector.draw_violations(
                            violation_frame, violations
                        )
                    elif persons:
                        violation_frame = self.ViolationDetector.draw_compliant_frame(
                            violation_frame, persons
                        )

                    # ✅ FIX: Store violation frame AFTER drawing
                    with self.frame_lock:
                        self.latest_violation_frame = violation_frame.copy()

                    try:
                        rgb_violation = cv2.cvtColor(violation_frame, cv2.COLOR_BGR2RGB)
                        self.violation_frame_callback(rgb_violation)
                    except Exception as e:
                        print(f"⚠️ Violation callback error: {e}")

            if self.save_enabled:
                # Decide which frame to save based on mode
                frame_to_save = clean_frame  # Default to detection frame
                
                # If Full Monitor: save violation frame (if available)
                if self.is_full_monitor_mode and self.ViolationDetector.enabled:
                    with self.frame_lock:
                        if self.latest_violation_frame is not None:
                            frame_to_save = self.latest_violation_frame.copy()
                            # Fallback to clean_frame if violation frame not ready
                            if frame_to_save is None:
                                frame_to_save = clean_frame
                        else:
                            frame_to_save = clean_frame
                
                # Save frames
                if self.save_type == "frames":
                    ts = datetime.datetime.now().strftime("%H-%M-%S-%f")[:-3]
                    frame_path = os.path.join(self.save_folder, f"{ts}.jpg")
                    cv2.imwrite(frame_path, frame_to_save)
            
                elif self.save_type == "video":
                    if self.video_writer is None:
                        h, w, _ = frame_to_save.shape
                        video_path = os.path.join(self.save_folder, "detection_output.mp4")
                        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
                        self.video_writer = cv2.VideoWriter(video_path, fourcc, 30, (w, h))
            
                        if not self.video_writer.isOpened():
                            print("âŒ Failed to open VideoWriter")
                            self.video_writer = None
                        else:
                            mode_type = "Violation" if self.is_full_monitor_mode else "Detection"
                            print(f"ðŸŽ¥ VideoWriter started ({w}x{h}) - Recording {mode_type} screen")
            
                    if self.video_writer:
                        self.video_writer.write(frame_to_save)

            current_time = time.time()
            if self.frame_callback and \
               (current_time - self._last_frame_callback_time >= self._callback_interval):

                self._last_frame_callback_time = current_time

                try:
                    rgb_clean = cv2.cvtColor(clean_frame, cv2.COLOR_BGR2RGB)
                    self.frame_callback(rgb_clean)
                except Exception as e:
                    print(f"⚠️ Frame callback error: {e}")
    
    def set_save_options(self, enabled: bool, save_type=None, save_folder=None):
        if enabled and save_type and save_type != self.save_type:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                print("🔄 VideoWriter released (save type changed)")
        
        self.save_enabled = enabled
        self.save_type = save_type
        self.save_folder = save_folder
    
        if not enabled:
            if self.video_writer:
                self.video_writer.release()
                self.video_writer = None
                print("🛑 VideoWriter released")
            print("🛑 Saving disabled")
            return
        
        if enabled:
            print(f"💾 Saving enabled → type={save_type}, folder={save_folder}")

    def set_full_monitor_mode(self, enabled=True):
        """Set whether we're in Full Monitor mode"""
        self.is_full_monitor_mode = enabled
        print(f" Full Monitor mode: {'ENABLED' if enabled else 'DISABLED'}")

    def run(self):
        threads = [
            threading.Thread(target=self.VideoFrameReader, daemon=True),
            threading.Thread(target=self.ObjectDetection, daemon=True),
            threading.Thread(target=self.ObjectTracking, daemon=True),
            threading.Thread(target=self.BoundingBox, daemon=True)
        ]
        for t in threads:
            t.start()

        while self.running and any(t.is_alive() for t in threads):
            time.sleep(0.1)

        self.Video.release()
        cv2.destroyAllWindows()
        print("✅ Backend exited cleanly.")

class ViolationDetector:
    """
    Real-time violation detection with compact item-by-item display
    """
    
    def __init__(self, model_names_dict, min_person_confidence=0.8):
        self.model_names = model_names_dict
        self.enabled = False
        self.required_classes = set()
        self.violation_callback = None
        
        self.min_person_confidence = min_person_confidence
        
        self.person_class_ids = [
            cls_id for cls_id, name in model_names_dict.items()
            if name.lower() == "person"
        ]
        
        self.total_violations = 0
        
        print(f"✅ ViolationDetector initialized (min confidence: {min_person_confidence})")
    
    def enable(self, enabled=True):
        self.enabled = enabled
        status = "ENABLED" if enabled else "DISABLED"
        print(f"🔴 Violation detection: {status}")
    
    def set_required_classes(self, class_names):
        self.required_classes = set(class_names)
        print(f"🔴 Checking classes: {self.required_classes}")
    
    def set_violation_callback(self, callback_fn):
        self.violation_callback = callback_fn
    
    def set_min_person_confidence(self, confidence):
        """Allow dynamic confidence threshold adjustment"""
        self.min_person_confidence = confidence
        print(f"🔧 Person confidence threshold set to: {confidence}")
    
    def is_negative_class(self, class_name):
        negative_prefixes = ["no ", "no-", "without ", "without-", "not ", "not-"]
        class_lower = class_name.lower()
        return any(class_lower.startswith(prefix) for prefix in negative_prefixes)
    
    def check_violations(self, yolo_results, frame_shape=None):
        """
        Check violations and return detailed item status for each person
        """
        if not self.enabled or not self.required_classes:
            return []
        
        # Collect all detected classes
        detected_classes = set()
        persons = []
        
        for result in yolo_results:
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cls_id = int(box.cls[0])
                cls_name = self.model_names[cls_id]
                conf = float(box.conf[0])
                
                detected_classes.add(cls_name)
                
                if cls_name.lower() == "person" and conf >= self.min_person_confidence:
                    persons.append({
                        "bbox": (x1, y1, x2, y2),
                        "confidence": conf
                    })
        
        violations = []
        
        for person in persons:
            # ✅ NEW: Check each required item individually
            present_items = []
            missing_items = []
            
            for required_class in self.required_classes:
                is_detected = required_class in detected_classes
                is_negative = self.is_negative_class(required_class)
                
                violation_detected = False
                
                if is_negative:
                    # Negative class (e.g., "no hard hat")
                    if is_detected:
                        violation_detected = True
                else:
                    # Positive class (e.g., "hard hat")
                    if not is_detected:
                        violation_detected = True
                
                if violation_detected:
                    missing_items.append(required_class)
                else:
                    present_items.append(required_class)
            
            # ✅ NEW: Include both missing AND present items
            if missing_items:
                violation = {
                    "person_bbox": person["bbox"],
                    "person_confidence": person["confidence"],
                    "missing": missing_items,
                    "present": present_items,  # ✅ NEW
                    "severity": self._calculate_severity_from_count(len(missing_items)),
                    "timestamp": datetime.datetime.now(),
                    "frame_shape": frame_shape,
                    "state_changed": True
                }
                violations.append(violation)
                self.total_violations += 1
        
        if len(violations) > 10:
            violations = violations[:10]
        
        if violations and self.violation_callback:
            try:
                self.violation_callback(violations)
            except Exception as e:
                print(f"❌ Violation callback error: {e}")
        
        return violations
    
    def _draw_check_symbol(self, frame, x, y, size, color):
        """Draw a check mark (✓) symbol"""
        # Check mark as two lines
        thickness = 2
        # First line (short, going down-right)
        cv2.line(frame, (x, y), (x + size//3, y + size//2), color, thickness)
        # Second line (long, going up-right)
        cv2.line(frame, (x + size//3, y + size//2), (x + size, y - size//3), color, thickness)

    def _draw_cross_symbol(self, frame, x, y, size, color):
        """Draw an X (cross) symbol"""
        thickness = 2
        # Diagonal line top-left to bottom-right
        cv2.line(frame, (x, y), (x + size, y + size), color, thickness)
        # Diagonal line top-right to bottom-left
        cv2.line(frame, (x + size, y), (x, y + size), color, thickness)

    def draw_violations(self, frame, violations):
        """
        ✅ FIXED: Compact display with proper check/cross symbols
        """
        if not violations:
            return frame

        # Group violations by person bbox
        person_violations = {}

        for violation in violations:
            bbox = violation["person_bbox"]
            bbox_key = tuple(bbox)

            if bbox_key not in person_violations:
                person_violations[bbox_key] = {
                    "bbox": bbox,
                    "missing": [],
                    "present": [],
                    "confidence": violation["person_confidence"]
                }

            person_violations[bbox_key]["missing"].extend(violation.get("missing", []))
            person_violations[bbox_key]["present"].extend(violation.get("present", []))

        for bbox_key, person_data in person_violations.items():
            x1, y1, x2, y2 = person_data["bbox"]
            missing_items = list(dict.fromkeys(person_data["missing"]))
            present_items = list(dict.fromkeys(person_data["present"]))
            conf = person_data["confidence"]

            # ✅ THIN RED BORDER
            border_color = (0, 0, 255)  # Red
            border_thickness = 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, border_thickness)

            # ✅ COMPACT DESIGN
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_thickness = 1
            line_height = 22
            padding = 8
            symbol_size = 10
            symbol_offset = 18  # Space for symbol

            # Calculate all items to display
            all_items = []

            # Add missing items with X
            for item in missing_items:
                all_items.append(("X", item, (0, 0, 255)))  # Red

            # Add present items with checkmark
            for item in present_items:
                all_items.append(("CHECK", item, (0, 255, 0)))  # Green

            if not all_items:
                continue
            
            # Calculate text box dimensions
            max_text_width = 0
            for symbol, item, _ in all_items:
                text = item  # Just the item name
                text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                max_text_width = max(max_text_width, text_size[0])

            box_width = max_text_width + symbol_offset + (padding * 2)
            box_height = (len(all_items) * line_height) + (padding * 2)

            # Position: top-right corner of person bbox
            label_x = x2 - box_width - 5
            label_y = y1

            # Adjust if out of bounds
            if label_x < 0:
                label_x = x1 + 5
            if label_y < 0:
                label_y = y2 - box_height
            if label_y + box_height > frame.shape[0]:
                label_y = frame.shape[0] - box_height - 5

            # ✅ SEMI-TRANSPARENT DARK BACKGROUND
            overlay = frame.copy()
            cv2.rectangle(
                overlay,
                (label_x, label_y),
                (label_x + box_width, label_y + box_height),
                (30, 30, 30),  # Dark gray
                -1
            )
            cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

            # ✅ THIN COLORED BORDER AROUND LABEL BOX
            cv2.rectangle(
                frame,
                (label_x, label_y),
                (label_x + box_width, label_y + box_height),
                border_color,
                1
            )

            # Draw items line by line
            y_offset = label_y + padding + 14

            for symbol, item, color in all_items:
                # Draw symbol (custom drawn)
                symbol_x = label_x + padding + 2
                symbol_y = y_offset - 8

                if symbol == "X":
                    # Draw X (cross)
                    self._draw_cross_symbol(frame, symbol_x, symbol_y, symbol_size, color)
                else:  # CHECK
                    # Draw checkmark
                    self._draw_check_symbol(frame, symbol_x, symbol_y, symbol_size, color)

                # Draw text
                text_x = label_x + padding + symbol_offset
                cv2.putText(
                    frame,
                    item,
                    (text_x, y_offset),
                    font,
                    font_scale,
                    color,
                    font_thickness,
                    cv2.LINE_AA
                )

                y_offset += line_height

        # ✅ BOTTOM STATUS BAR
        total_violations = sum(len(p["missing"]) for p in person_violations.values())
        count_text = f"Violations: {total_violations} | Persons: {len(person_violations)}"

        font_scale_small = 0.6
        text_size = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, font_scale_small, 2)[0]
        text_x = 10
        text_y = frame.shape[0] - 15

        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(
            overlay,
            (text_x - 5, text_y - text_size[1] - 5),
            (text_x + text_size[0] + 5, text_y + 5),
            (0, 0, 0),
            -1
        )
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        cv2.putText(
            frame,
            count_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale_small,
            (255, 255, 255),
            2
        )

        return frame

    def draw_compliant_frame(self, frame, persons):
        """
        ✅ FIXED: Compact compliant display with proper checkmark symbols
        """
        for person in persons:
            x1, y1, x2, y2 = person["bbox"]
            conf = person["confidence"]

            if conf < self.min_person_confidence:
                continue
            
            # ✅ THIN GREEN BORDER
            border_color = (0, 255, 0)  # Green
            border_thickness = 2

            cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, border_thickness)

            # ✅ COMPACT DESIGN
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            font_thickness = 1
            line_height = 22
            padding = 8
            symbol_size = 10
            symbol_offset = 18

            # All items present
            all_items = []
            for item in self.required_classes:
                all_items.append(("CHECK", item, (0, 255, 0)))

            if not all_items:
                # Just show compliant text with checkmark
                label_text = "COMPLIANT"
                text_size = cv2.getTextSize(label_text, font, 0.55, font_thickness + 1)[0]
                text_x = x1 + 5 + 18
                text_y = y1 - 8

                if text_y < 15:
                    text_y = y2 + 20

                # Background
                overlay = frame.copy()
                cv2.rectangle(
                    overlay,
                    (text_x - 18 - 3, text_y - text_size[1] - 3),
                    (text_x + text_size[0] + 3, text_y + 3),
                    (30, 30, 30),
                    -1
                )
                cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

                # Draw checkmark
                self._draw_check_symbol(frame, text_x - 16, text_y - 8, 12, (0, 255, 0))

                # Draw text
                cv2.putText(frame, label_text, (text_x, text_y), font, 0.55, (0, 255, 0), font_thickness + 1, cv2.LINE_AA)
                continue
            
            # Calculate text box dimensions
            max_text_width = 0
            for symbol, item, _ in all_items:
                text = item
                text_size = cv2.getTextSize(text, font, font_scale, font_thickness)[0]
                max_text_width = max(max_text_width, text_size[0])

            box_width = max_text_width + symbol_offset + (padding * 2)
            box_height = (len(all_items) * line_height) + (padding * 2)

            # Position: top-right corner
            label_x = x2 - box_width - 5
            label_y = y1

            # Adjust if out of bounds
            if label_x < 0:
                label_x = x1 + 5
            if label_y < 0:
                label_y = y2 - box_height
            if label_y + box_height > frame.shape[0]:
                label_y = frame.shape[0] - box_height - 5

            # ✅ SEMI-TRANSPARENT DARK BACKGROUND
            overlay = frame.copy()
            cv2.rectangle(
                overlay,
                (label_x, label_y),
                (label_x + box_width, label_y + box_height),
                (30, 30, 30),
                -1
            )
            cv2.addWeighted(overlay, 0.85, frame, 0.15, 0, frame)

            # ✅ THIN GREEN BORDER
            cv2.rectangle(
                frame,
                (label_x, label_y),
                (label_x + box_width, label_y + box_height),
                border_color,
                1
            )

            # Draw items
            y_offset = label_y + padding + 14

            for symbol, item, color in all_items:
                # Draw checkmark symbol
                symbol_x = label_x + padding + 2
                symbol_y = y_offset - 8

                self._draw_check_symbol(frame, symbol_x, symbol_y, symbol_size, color)

                # Draw text
                text_x = label_x + padding + symbol_offset
                cv2.putText(
                    frame,
                    item,
                    (text_x, y_offset),
                    font,
                    font_scale,
                    color,
                    font_thickness,
                    cv2.LINE_AA
                )

                y_offset += line_height

        return frame

    def _calculate_severity_from_count(self, count):
        if count >= 4:
            return "CRITICAL"
        elif count >= 3:
            return "HIGH"
        elif count >= 2:
            return "MEDIUM"
        else:
            return "LOW"
    
    def get_statistics(self):
        return {
            "total_violations": self.total_violations,
            "enabled": self.enabled,
            "required_classes": list(self.required_classes),
            "min_person_confidence": self.min_person_confidence
        }
    
    def reset_statistics(self):
        self.total_violations = 0
        print("📊 Violation statistics reset")

class UI:
    def __init__(self, source=0, model_path="Local_2.pt",tracking_path=None, use_gpu=False,log_callback=None):
        self.log_callback=log_callback
        self.Mode = None
        self.active_mode = None
        self.backend = Main_App(Video_path=source, Model_path=model_path,tracking_path=tracking_path,use_gpu=use_gpu,QueueSize=5,log_callback=log_callback)
    
    def set_violation_classes(self, class_names):
        self.backend.set_violation_classes(class_names)
    
    def enable_violation_detection(self, enabled=True):
        self.backend.enable_violation_detection(enabled)
    
    def send_log(self, message, log_type="INFO"):
        """Internal logging method"""
        if self.log_callback:
            try:
                self.log_callback(message, log_type)
            except:
                pass

    def set_violation_callback(self, callback_fn):
        self.backend.set_violation_callback(callback_fn)
    
    def set_violation_frame_callback(self, callback_fn):
        self.backend.set_violation_frame_callback(callback_fn)
    
    def get_violation_statistics(self):
        return self.backend.ViolationDetector.get_statistics()
    
    def start_mode(self, mode):
        self.Mode = mode
        self.active_mode = mode
        self.send_log(f"▶ {mode} started")
    
    def stop_mode(self, mode):
        if mode == "full_monitor":
            if self.Mode == "tracking":
                self.Mode = None
            self.send_log("🛑 Full Monitoring stopped")
            self.send_log("🛑 Detection stopped")
            self.send_log("🛑 Tracking stopped")
        elif mode == "tracking":
            if self.Mode == "tracking":
                self.Mode = "detection"
            self.send_log("🛑 Tracking stopped")
        elif mode == "detection":
            if self.Mode == "detection":
                self.Mode = None
            self.send_log("🛑 Detection stopped")
    
    def stop_all_modes(self):
        self.Mode = None
        self.active_mode = None
        self.send_log("🛑 All modes stopped")

    def setMode(self, mode):
        self.send_log("BACKEND RECEIVED MODE:", mode)
        self.backend.set_mode(mode)

    def run(self):
        self.backend.run()
   
    def set_save_enabled(self, enabled: bool):
        if self.backend:
            self.backend.set_save_options(enabled)
    
    def stop(self):
        self.backend.running = False
        self.backend.Video.release()
        self.backend.run()
