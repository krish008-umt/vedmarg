import pyaudio
import numpy as np
import opensmile
import threading
import queue
import time
import json

class VoiceEmotionDetector:
    def __init__(self):
        # Audio parameters
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.record_seconds = 2  # Analyze every 2 seconds
        
        # OpenSmile setup
        self.smile = opensmile.Smile(
            feature_set=opensmile.FeatureSet.emobase,
            feature_level=opensmile.FeatureLevel.Functionals,
        )
        
        # Current emotion only (no history)
        self.current_emotion = "neutral"
        self.emotion_confidence = 0.0
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.is_recording = False
        
    def setup_audio(self):
        """Initialize audio stream"""
        self.audio = pyaudio.PyAudio()
        self.stream = self.audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=self.audio_callback
        )
    
    def audio_callback(self, in_data, frame_count, time_info, status):
        """Audio stream callback"""
        if self.is_recording:
            self.audio_queue.put(in_data)
        return (in_data, pyaudio.paContinue)
    
    def extract_audio_features(self, audio_data):
        """Extract features using OpenSmile"""
        try:
            # Convert bytes to numpy array
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_np.astype(np.float32) / 32768.0
            
            # Extract features using OpenSmile
            features = self.smile.process_signal(audio_float, self.rate)
            return features
            
        except Exception as e:
            return None
    
    def features_to_emotion(self, features):
        """Convert OpenSmile features to emotion"""
        try:
            feature_dict = features.iloc[0].to_dict()
            
            # Extract key features
            pitch_mean = feature_dict.get('F0final_sma_amean', 120)
            pitch_std = feature_dict.get('F0final_sma_std', 20)
            intensity_mean = feature_dict.get('pcm_LOGenergy_sma_amean', 0)
            intensity_std = feature_dict.get('pcm_LOGenergy_sma_std', 0)
            spectral_centroid = feature_dict.get('spectralCentroid_sma_amean', 0)
            spectral_flux = feature_dict.get('spectralFlux_sma_amean', 0)
            
            # Emotion decision logic
            emotion_scores = {
                'happy': 0,
                'sad': 0,
                'angry': 0,
                'fear': 0,
                'surprised': 0,
                'neutral': 0
            }
            
            # Happy: higher pitch, moderate intensity, stable voice
            if pitch_mean > 180 and intensity_std < 0.1:
                emotion_scores['happy'] += 3
            if spectral_centroid > 2000:
                emotion_scores['happy'] += 2
            
            # Sad: lower pitch, low intensity, monotone
            if pitch_mean < 100 and intensity_mean < 0.05:
                emotion_scores['sad'] += 3
            if pitch_std < 15:
                emotion_scores['sad'] += 2
            
            # Angry: high intensity, high pitch variability
            if intensity_mean > 0.15 and pitch_std > 40:
                emotion_scores['angry'] += 3
            if spectral_flux > 0.2:
                emotion_scores['angry'] += 2
            
            # Fear: high pitch, high spectral centroid, unstable
            if pitch_mean > 200 and pitch_std > 30:
                emotion_scores['fear'] += 3
            if spectral_centroid > 2500:
                emotion_scores['fear'] += 2
            
            # Surprised: sudden intensity changes
            if intensity_std > 0.2 and spectral_flux > 0.15:
                emotion_scores['surprised'] += 3
            
            # Neutral: moderate values
            if (100 <= pitch_mean <= 180 and 
                0.05 <= intensity_mean <= 0.1 and 
                pitch_std < 25):
                emotion_scores['neutral'] += 3
            
            # Find dominant emotion
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            max_score = emotion_scores[dominant_emotion]
            total_score = sum(emotion_scores.values())
            
            confidence = (max_score / total_score * 100) if total_score > 0 else 0
            
            return dominant_emotion, confidence
            
        except Exception as e:
            return "neutral", 0.0
    
    def output_emotion_json(self, emotion, confidence):
        """Output emotion data as JSON for backend"""
        emotion_data = {
            "emotion": emotion,
            "confidence": round(confidence, 1),
            "timestamp": time.time()
        }
        print(json.dumps(emotion_data))
    
    def process_audio(self):
        """Main audio processing loop"""
        audio_buffer = []
        target_frames = int(self.rate * self.record_seconds / self.chunk)
        
        while self.is_recording:
            try:
                # Collect audio data
                data = self.audio_queue.get(timeout=1)
                audio_buffer.append(data)
                
                # Process when we have enough data
                if len(audio_buffer) >= target_frames:
                    audio_data = b''.join(audio_buffer)
                    
                    # Extract features and classify emotion
                    features = self.extract_audio_features(audio_data)
                    if features is not None:
                        emotion, confidence = self.features_to_emotion(features)
                        
                        # Update current emotion
                        self.current_emotion = emotion
                        self.emotion_confidence = confidence
                        
                        # Output only emotion and confidence for backend
                        self.output_emotion_json(emotion, confidence)
                    
                    audio_buffer = []  # Reset buffer
                    
            except queue.Empty:
                continue
    
    def start(self):
        """Start voice emotion detection"""
        print("Voice Emotion Detector Started (Backend Mode)", file=sys.stderr)
        print("Output format: JSON with emotion and confidence", file=sys.stderr)
        
        try:
            self.setup_audio()
            self.is_recording = True
            
            # Start audio processing thread
            audio_thread = threading.Thread(target=self.process_audio)
            audio_thread.daemon = True
            audio_thread.start()
            
            # Keep main thread alive
            while self.is_recording:
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            pass
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
        finally:
            self.stop()
    
    def stop(self):
        """Stop voice emotion detection"""
        self.is_recording = False
        if hasattr(self, 'stream'):
            self.stream.stop_stream()
            self.stream.close()
        if hasattr(self, 'audio'):
            self.audio.terminate()
        print("Voice emotion detector stopped.", file=sys.stderr)


# Simple version for backend use
class SimpleVoiceEmotionDetector:
    def __init__(self):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 1024
        self.current_emotion = "neutral"
        self.is_recording = False
    
    def analyze_simple(self, audio_data):
        """Simple analysis based on volume and variability"""
        # Convert to numpy array
        audio_np = np.frombuffer(audio_data, dtype=np.int16)
        
        # Calculate volume (RMS)
        volume = np.sqrt(np.mean(audio_np**2))
        
        # Calculate variability (standard deviation)
        variability = np.std(audio_np)
        
        # Simple emotion mapping
        if volume < 1000:
            return "silent", 0
        elif volume > 10000 and variability > 5000:
            return "excited", 80
        elif volume > 15000:
            return "angry", 85
        elif volume < 3000 and variability < 1000:
            return "calm", 75
        elif 5000 < volume < 10000:
            return "neutral", 70
        else:
            return "talking", 60
    
    def output_emotion_json(self, emotion, confidence):
        """Output emotion data as JSON for backend"""
        emotion_data = {
            "emotion": emotion,
            "confidence": confidence,
            "timestamp": time.time()
        }
        print(json.dumps(emotion_data))
    
    def start_detection(self):
        """Simple voice emotion detection for backend"""
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk
        )
        
        self.is_recording = True
        print("Simple Voice Emotion Detector Started (Backend Mode)", file=sys.stderr)
        
        try:
            while self.is_recording:
                # Read audio data
                data = stream.read(self.chunk, exception_on_overflow=False)
                emotion, confidence = self.analyze_simple(data)
                self.current_emotion = emotion
                
                # Output only emotion and confidence for backend
                self.output_emotion_json(emotion, confidence)
                
        except KeyboardInterrupt:
            pass
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
            print("Detector stopped.", file=sys.stderr)


# Import sys for stderr output
import sys

# Run the detector
if __name__ == "__main__":
    # Try the OpenSmile version first
    try:
        detector = VoiceEmotionDetector()
        detector.start()
    except Exception as e:
        print(f"OpenSmile detector failed: {e}", file=sys.stderr)
        print("Falling back to simple detector...", file=sys.stderr)
        simple_detector = SimpleVoiceEmotionDetector()
        simple_detector.start_detection()