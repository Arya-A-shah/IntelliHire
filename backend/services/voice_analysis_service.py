import numpy as np
import base64
from typing import List, Dict, Any

async def analyze_audio_chunk(audio_data: bytes, sid: str, sio) -> None:
    """
    Optional: Analyze audio in real-time as chunks arrive
    Can be used for live feedback
    """
    pass  # Implement if needed for real-time analysis

async def finalize_voice_analysis(audio_chunks: List[bytes], sample_rate: int, sid: str) -> Dict[str, Any]:
    """
    Perform comprehensive voice analysis on complete audio recording
    """
    try:
        # Combine all audio chunks
        combined_audio = b''.join(audio_chunks)
        
        # Convert bytes to numpy array (assuming PCM16)
        audio_array = np.frombuffer(combined_audio, dtype=np.int16)
        
        # Normalize audio
        audio_float = audio_array.astype(np.float32) / 32768.0
        
        # Perform various analyses
        analysis_results = {
            "duration": len(audio_float) / sample_rate,
            "sample_rate": sample_rate,
            "total_samples": len(audio_float),
        }
        
        # 1. Volume/Energy Analysis
        rms_energy = np.sqrt(np.mean(audio_float ** 2))
        analysis_results["average_volume"] = float(rms_energy)
        analysis_results["peak_volume"] = float(np.max(np.abs(audio_float)))
        
        # 2. Speech Rate Analysis (simple approximation based on zero crossings)
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_float)))) / 2
        zcr_rate = zero_crossings / len(audio_float) * sample_rate
        analysis_results["zero_crossing_rate"] = float(zcr_rate)
        
        # 3. Silence Detection
        silence_threshold = 0.01
        silence_samples = np.sum(np.abs(audio_float) < silence_threshold)
        silence_percentage = (silence_samples / len(audio_float)) * 100
        analysis_results["silence_percentage"] = float(silence_percentage)
        
        # 4. Confidence/Clarity Indicators
        # Based on energy consistency
        frame_size = int(0.025 * sample_rate)  # 25ms frames
        hop_size = int(0.010 * sample_rate)    # 10ms hop
        
        frame_energies = []
        for i in range(0, len(audio_float) - frame_size, hop_size):
            frame = audio_float[i:i + frame_size]
            frame_energy = np.sqrt(np.mean(frame ** 2))
            frame_energies.append(frame_energy)
        
        if frame_energies:
            energy_variance = np.var(frame_energies)
            analysis_results["energy_variance"] = float(energy_variance)
            analysis_results["clarity_score"] = float(1.0 / (1.0 + energy_variance * 100))  # Higher is clearer
        
        # 5. Speaking Pace Estimation
        # Approximate based on energy fluctuations
        active_frames = [e for e in frame_energies if e > silence_threshold]
        if active_frames:
            analysis_results["active_speech_ratio"] = len(active_frames) / len(frame_energies)
            analysis_results["estimated_pace"] = "normal"  # Can be enhanced with ML models
            
            # Simple pace estimation
            if len(active_frames) / len(frame_energies) > 0.8:
                analysis_results["estimated_pace"] = "fast"
            elif len(active_frames) / len(frame_energies) < 0.5:
                analysis_results["estimated_pace"] = "slow"
        
        # 6. Confidence Indicators
        # Combine multiple factors for confidence score
        confidence_score = 0.0
        
        # Volume confidence (louder = more confident, but not too loud)
        if 0.1 < rms_energy < 0.5:
            confidence_score += 0.3
        elif rms_energy >= 0.05:
            confidence_score += 0.15
            
        # Clarity confidence
        if "clarity_score" in analysis_results:
            confidence_score += analysis_results["clarity_score"] * 0.3
            
        # Silence confidence (less silence = more confident)
        if silence_percentage < 20:
            confidence_score += 0.2
        elif silence_percentage < 40:
            confidence_score += 0.1
            
        # Pace confidence (moderate pace = more confident)
        if "active_speech_ratio" in analysis_results:
            if 0.5 < analysis_results["active_speech_ratio"] < 0.85:
                confidence_score += 0.2
                
        analysis_results["confidence_score"] = min(1.0, confidence_score)
        
        # 7. Overall Assessment
        if confidence_score > 0.7:
            analysis_results["overall_assessment"] = "confident"
        elif confidence_score > 0.4:
            analysis_results["overall_assessment"] = "moderate"
        else:
            analysis_results["overall_assessment"] = "hesitant"
        
        print(f"Voice analysis complete for {sid}: confidence={confidence_score:.2f}")
        
        return analysis_results
        
    except Exception as e:
        print(f"Error in voice analysis: {e}")
        return {
            "error": str(e),
            "status": "analysis_failed"
        }