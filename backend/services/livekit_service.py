import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
import cv2
import numpy as np
from beanie import PydanticObjectId
from collections import deque
from datetime import datetime, timedelta
from livekit import api, rtc
from config import settings
from core.socket import sio
from services.video_processor import analyze_frame
from sharedstate import active_processors, active_sessions

# FIX: MediaPipe is CPU-heavy and synchronous. Run it on ONE background thread
# (MediaPipe's face models are not safe to call from several threads at once),
# so the async event loop keeps serving sockets while a frame is analysed.
_cv_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="cv")

LIVEKIT_URL = settings.LIVEKIT_URL
LIVEKIT_API_KEY = settings.LIVEKIT_API_KEY
LIVEKIT_API_SECRET = settings.LIVEKIT_API_SECRET
PROC_NS = "/proc"


def frame_to_bgr(frame):
    """Convert LiveKit VideoFrame to OpenCV BGR image."""
    if frame is None:
        return None

    try:
        width = frame.width
        height = frame.height

        if hasattr(frame, 'data'):
            frame_data = frame.data
            y_plane_size = width * height
            uv_plane_size = (width // 2) * (height // 2)
            frame_array = np.frombuffer(frame_data, dtype=np.uint8)

            expected_size = y_plane_size + (2 * uv_plane_size)
            if len(frame_array) >= expected_size:
                y_plane = frame_array[:y_plane_size].reshape((height, width))
                u_plane = frame_array[y_plane_size:y_plane_size +
                                      uv_plane_size].reshape((height // 2, width // 2))
                v_plane = frame_array[y_plane_size + uv_plane_size:y_plane_size + (
                    2 * uv_plane_size)].reshape((height // 2, width // 2))

                u_upsampled = cv2.resize(
                    u_plane, (width, height), interpolation=cv2.INTER_LINEAR)
                v_upsampled = cv2.resize(
                    v_plane, (width, height), interpolation=cv2.INTER_LINEAR)

                yuv_image = cv2.merge([y_plane, u_upsampled, v_upsampled])
                bgr_image = cv2.cvtColor(yuv_image, cv2.COLOR_YUV2BGR)
                return bgr_image

        if hasattr(frame, 'to_argb'):
            argb_frame = frame.to_argb()
            if hasattr(argb_frame, 'data'):
                argb_array = np.frombuffer(
                    argb_frame.data, dtype=np.uint8).reshape((height, width, 4))
                bgr_image = argb_array[:, :, 1:4][:, :, ::-1]
                return bgr_image

        return None

    except Exception as e:
        print(f"[frame_to_bgr] Error: {e}")
        return None


class EventThrottler:
    """Throttles events to prevent spam and ensure meaningful detections."""

    def __init__(self, cooldown_seconds=5, persistence_threshold=3):
        self.cooldown_seconds = cooldown_seconds
        self.persistence_threshold = persistence_threshold
        self.event_history = {}  # {event_type: deque of timestamps}
        self.last_emitted = {}  # {event_type: last emit timestamp}
        self.event_counters = {}  # {event_type: consecutive count}

    def should_emit_event(self, event_type):
        """
        Check if event should be emitted based on:
        1. Persistence: Event must occur multiple times consecutively
        2. Cooldown: Don't spam same event too frequently
        """
        current_time = datetime.now()

        # Initialize if new event type
        if event_type not in self.event_counters:
            self.event_counters[event_type] = 0
            self.last_emitted[event_type] = None
            self.event_history[event_type] = deque(maxlen=10)

        # Increment counter for persistence check
        self.event_counters[event_type] += 1

        # Check if event has persisted long enough
        if self.event_counters[event_type] < self.persistence_threshold:
            return False

        # Check cooldown period
        if self.last_emitted[event_type]:
            time_since_last = (
                current_time - self.last_emitted[event_type]).total_seconds()
            if time_since_last < self.cooldown_seconds:
                return False

        # Event passed all checks
        self.last_emitted[event_type] = current_time
        self.event_history[event_type].append(current_time)
        return True

    def reset_counter(self, event_type):
        """Reset counter when event stops occurring."""
        if event_type in self.event_counters:
            self.event_counters[event_type] = 0


class IntegrityScoreTracker:
    """
    Tracks integrity score using 30-second window approach.

    Windows: Divides interview into 30-second intervals
    Counts: Number of alerts per window
    Score: Average/Median of all window counts
    """

    def __init__(self, window_duration_seconds=30, window_threshold=4, total_threshold=2.5):
        """
        Args:
            window_duration_seconds: Duration of each window (default: 30)
            window_threshold: Max alerts per window before flagging (default: 4)
            total_threshold: Max average alerts across all windows (default: 2.5)
        """
        self.window_duration = window_duration_seconds
        self.window_threshold = window_threshold
        self.total_threshold = total_threshold

        self.windows = []  # List of window data
        self.current_window = {
            "start_time": datetime.now(),
            "end_time": None,
            "alerts": [],
            "alert_count": 0
        }
        self.interview_start_time = datetime.now()

    def add_alert(self, event_type, timestamp=None):
        """Add an alert to the current window."""
        if timestamp is None:
            timestamp = datetime.now()

        # Check if current window has expired
        time_since_window_start = (
            timestamp - self.current_window["start_time"]).total_seconds()

        if time_since_window_start >= self.window_duration:
            # Close current window and start new one
            self._close_current_window()
            self.current_window = {
                "start_time": timestamp,
                "end_time": None,
                "alerts": [],
                "alert_count": 0
            }

        # Add alert to current window
        self.current_window["alerts"].append({
            "type": event_type,
            "timestamp": timestamp.isoformat()
        })
        self.current_window["alert_count"] += 1

    def _close_current_window(self):
        """Close the current window and add it to history."""
        self.current_window["end_time"] = datetime.now()
        self.windows.append({
            "window_number": len(self.windows) + 1,
            "start_time": self.current_window["start_time"].isoformat(),
            "end_time": self.current_window["end_time"].isoformat(),
            "alert_count": self.current_window["alert_count"],
            "alerts": self.current_window["alerts"],
            "exceeds_threshold": self.current_window["alert_count"] > self.window_threshold
        })

        print(
            f"[Integrity] Window #{len(self.windows)} closed: {self.current_window['alert_count']} alerts")

        # FIX: start a fresh window. Before, the closed window stayed "current",
        # so asking for the report twice counted the same alerts twice.
        self.current_window = {
            "start_time": self.current_window["end_time"],
            "end_time": None,
            "alerts": [],
            "alert_count": 0
        }

    def get_integrity_score(self, use_median=False):
        """
        Calculate integrity score based on alert frequency.

        Args:
            use_median: If True, use median instead of average

        Returns:
            dict with score details
        """
        # Close current window for calculation
        if self.current_window["alert_count"] > 0:
            temp_end_time = datetime.now()
            time_in_current = (
                temp_end_time - self.current_window["start_time"]).total_seconds()

            # FIX: always include the open window if it has alerts (the old
            # 10-second rule dropped alerts from the last seconds of the interview)
            if True:
                temp_window = {
                    "window_number": len(self.windows) + 1,
                    "start_time": self.current_window["start_time"].isoformat(),
                    "end_time": temp_end_time.isoformat(),
                    "alert_count": self.current_window["alert_count"],
                    "alerts": self.current_window["alerts"],
                    "exceeds_threshold": self.current_window["alert_count"] > self.window_threshold
                }
                all_windows = self.windows + [temp_window]
            else:
                all_windows = self.windows
        else:
            all_windows = self.windows

        # Extract alert counts from all windows
        alert_counts = [w["alert_count"] for w in all_windows]

        # FIX: windows are only created when an alert arrives, so quiet 30-second
        # stretches were never counted. One bad moment in a 10-minute interview
        # averaged as if the whole interview was bad. Pad with zero-alert windows
        # up to the real number of 30-second windows that have passed.
        elapsed = (datetime.now() - self.interview_start_time).total_seconds()
        expected_windows = max(1, math.ceil(elapsed / self.window_duration))
        alert_counts += [0] * max(0, expected_windows - len(alert_counts))
        total_alerts = sum(alert_counts)

        # Calculate statistics
        average = sum(alert_counts) / len(alert_counts)
        sorted_counts = sorted(alert_counts)
        n = len(sorted_counts)

        if n % 2 == 0:
            median = (sorted_counts[n//2 - 1] + sorted_counts[n//2]) / 2
        else:
            median = sorted_counts[n//2]

        max_alerts = max(alert_counts)
        min_alerts = min(alert_counts)

        # Count violations
        windows_exceeding = sum(
            1 for count in alert_counts if count > self.window_threshold)

        # Determine final score (use median or average)
        final_score = median if use_median else average

        # Determine grade and status
        if final_score <= 1.0:
            grade = "A"
            status = "Excellent"
        elif final_score <= 2.0:
            grade = "B"
            status = "Good"
        elif final_score <= 3.0:
            grade = "C"
            status = "Fair"
        elif final_score <= 4.0:
            grade = "D"
            status = "Poor"
        else:
            grade = "F"
            status = "Critical"

        # Check if exceeds total threshold
        exceeds_total_threshold = final_score > self.total_threshold

        interview_duration = (
            datetime.now() - self.interview_start_time).total_seconds()

        return {
            "score": round(final_score, 2),
            "total_windows": len(alert_counts),
            "alert_counts": alert_counts,
            "average": round(average, 2),
            "median": round(median, 2),
            "max": max_alerts,
            "min": min_alerts,
            "windows_exceeding_threshold": windows_exceeding,
            "window_threshold": self.window_threshold,
            "total_threshold": self.total_threshold,
            "exceeds_total_threshold": exceeds_total_threshold,
            "total_alerts": total_alerts,
            "interview_duration_seconds": round(interview_duration, 2),
            "grade": grade,
            "status": status,
            "calculation_method": "median" if use_median else "average"
        }

    def get_detailed_report(self):
        """Get detailed window-by-window report."""
        # Close current window temporarily for reporting
        self._close_current_window(
        ) if self.current_window["alert_count"] > 0 else None

        return {
            "windows": self.windows,
            "current_window": self.current_window,
            "integrity_score": self.get_integrity_score(),
            "window_duration_seconds": self.window_duration,
            "interview_start_time": self.interview_start_time.isoformat()
        }


class LiveKitVideoProcessor:
    """LiveKit room processor with intelligent event detection and integrity scoring."""

    def __init__(self, interview_id: str, room_name: str):
        self.interview_id = interview_id
        self.room_name = room_name
        self.room = None
        self.running = False
        self.frame_count = 0
        # Analyze every 30th frame (~1 per second at 30fps)
        self.analysis_interval = 30
        self.throttler = EventThrottler(
            cooldown_seconds=10, persistence_threshold=2)
        self.previous_events = set()

        # Initialize integrity tracker
        self.integrity_tracker = IntegrityScoreTracker(
            window_duration_seconds=30,
            window_threshold=4,
            total_threshold=2.5
        )

    async def connect(self):
        """Connect to LiveKit room as server participant (observer)."""
        try:
            token = api.AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET)
            token.with_identity(f"analyzer_{self.interview_id}")
            token.with_name("Video Analyzer")
            token.with_grants(
                api.VideoGrants(
                    room_join=True,
                    room=self.room_name,
                    can_publish=False,
                    can_subscribe=True,
                )
            )
            jwt_token = token.to_jwt()

            self.room = rtc.Room()

            @self.room.on("track_subscribed")
            def on_track_subscribed(track, publication, participant):
                if track.kind == rtc.TrackKind.KIND_VIDEO:
                    print(
                        f"✅ Subscribed to video track of {participant.identity}")
                    asyncio.create_task(
                        self.process_video_track(track, participant))

            @self.room.on("participant_connected")
            def on_participant_connected(participant):
                print(f"👤 Participant connected: {participant.identity}")
                asyncio.create_task(
                    sio.emit(
                        "participant_joined",
                        {"interview_id": self.interview_id,
                            "participant": participant.identity},
                        room=f"interview_{self.interview_id}",
                        namespace=PROC_NS,
                    )
                )

            @self.room.on("participant_disconnected")
            def on_participant_disconnected(participant):
                print(f"👋 Participant disconnected: {participant.identity}")
                asyncio.create_task(
                    sio.emit(
                        "participant_left",
                        {"interview_id": self.interview_id,
                            "participant": participant.identity},
                        room=f"interview_{self.interview_id}",
                        namespace=PROC_NS,
                    )
                )

            await self.room.connect(LIVEKIT_URL, jwt_token)
            print(f"🎥 Connected to LiveKit room: {self.room_name}")
            self.running = True

        except Exception as e:
            print(f"❌ Error connecting to LiveKit: {e}")
            import traceback
            traceback.print_exc()
            raise

    async def process_video_track(self, track: rtc.VideoTrack, participant):
        """Process video frames with intelligent throttling and integrity tracking."""
        video_stream = rtc.VideoStream(track)
        print(f"🎬 Starting video processing for {participant.identity}")

        try:
            async for frame_event in video_stream:
                if not self.running:
                    break

                self.frame_count += 1

                # Analyze less frequently
                if self.frame_count % self.analysis_interval != 0:
                    continue

                frame = frame_event.frame if hasattr(
                    frame_event, 'frame') else frame_event
                if frame is None:
                    continue

                bgr_frame = frame_to_bgr(frame)
                if bgr_frame is None:
                    continue

                # Run analysis
                try:
                    loop = asyncio.get_running_loop()
                    raw_events = await loop.run_in_executor(
                        _cv_executor, analyze_frame, bgr_frame)
                    current_events = set(raw_events)

                    # Reset counters for events that stopped
                    stopped_events = self.previous_events - current_events
                    for event in stopped_events:
                        self.throttler.reset_counter(event)

                    # Filter events through throttler
                    events_to_emit = []
                    for event in raw_events:
                        if self.throttler.should_emit_event(event):
                            events_to_emit.append(event)

                    self.previous_events = current_events

                    # Only emit if we have events that passed throttling
                    if events_to_emit:
                        timestamp_sec = self.frame_count / 30.0

                        # Format events with better messages
                        formatted_events = self._format_events(events_to_emit)

                        # Add ONLY throttled events to integrity tracker
                        for event in events_to_emit:
                            self.integrity_tracker.add_alert(event)

                        # Get current integrity score for logging
                        integrity_score = self.integrity_tracker.get_integrity_score()

                        # Emit events without integrity score (no frontend display)
                        await sio.emit(
                            "analysis_events",
                            {
                                "interview_id": str(self.interview_id),
                                "participant": participant.identity,
                                "events": formatted_events,
                                "timestamp": timestamp_sec,
                                "frame_count": self.frame_count,
                            },
                            room=f"interview_{str(self.interview_id)}",
                            namespace=PROC_NS,
                        )

                        # Log integrity score to console for testing
                        print(
                            f"🚨 [{datetime.now().strftime('%H:%M:%S')}] Events: {formatted_events}"
                        )
                        print(
                            f"📊 [INTEGRITY] Score: {integrity_score['score']} | "
                            f"Grade: {integrity_score['grade']} ({integrity_score['status']}) | "
                            f"Windows: {integrity_score['total_windows']} | "
                            f"Counts: {integrity_score['alert_counts']}"
                        )

                        # Store in session
                        session = active_sessions.setdefault(
                            self.interview_id, {})
                        session.setdefault("event_history", []).append(
                            {
                                "events": formatted_events,
                                "timestamp": timestamp_sec,
                                "frame_count": self.frame_count,
                                "time": datetime.now().isoformat()
                            }
                        )

                except Exception as e:
                    print(f"❌ Error analyzing frame: {e}")

        except Exception as e:
            print(f"❌ Error in video track processing: {e}")
            import traceback
            traceback.print_exc()

    def _format_events(self, events):
        """Format events with user-friendly messages."""
        event_messages = {
            "no_face_detected": "⚠️ Face not visible in frame",
            "multiple_faces_detected": "🚨 Multiple people detected",
            "looking_sideways": "👀 Looking away from screen",
            "looking_left": "← Looking left",
            "looking_right": "→ Looking right",
            "looking_down": "↓ Looking down",
            "looking_up": "↑ Looking up",
            "head_tilted": "⚠️ Unusual head position",
            "eyes_closed": "😴 Eyes closed",
            "talking": "🗣️ Talking detected",
            "face_too_close": "📏 Too close to camera",
            "face_too_far": "📏 Too far from camera",
            "gaze_away": "👁️ Eyes not on screen",
            "face_not_centered": "⚠️ Face not properly positioned",
            "possible_hand_near_face": "✋ Hand near face",
            "gaze_left": "👁️ Looking left (gaze)",
            "gaze_right": "👁️ Looking right (gaze)",
        }

        return [event_messages.get(e, f"⚠️ {e}") for e in events]

    def get_integrity_score(self):
        """Get current integrity score."""
        return self.integrity_tracker.get_integrity_score()

    def get_detailed_integrity_report(self):
        """Get detailed integrity report with all windows."""
        return self.integrity_tracker.get_detailed_report()

    async def disconnect(self):
        """Disconnect from LiveKit room."""
        self.running = False

        # Get final integrity score before disconnecting
        final_score = self.get_integrity_score()
        print(f"\n{'='*60}")
        print(f"[Integrity] Final Score for Interview {self.interview_id}")
        print(
            f"[Integrity] Score: {final_score['score']} ({final_score['grade']})")
        print(f"[Integrity] Status: {final_score['status']}")
        print(f"[Integrity] Windows: {final_score['total_windows']}")
        print(
            f"[Integrity] Average: {final_score['average']}, Median: {final_score['median']}")
        print(f"[Integrity] Alert Counts: {final_score['alert_counts']}")
        print(f"{'='*60}\n")

        # Store final score in session
        if self.interview_id in active_sessions:
            active_sessions[self.interview_id]["final_integrity_score"] = final_score
            active_sessions[self.interview_id]["detailed_integrity_report"] = self.get_detailed_integrity_report()

        if self.room:
            await self.room.disconnect()
            print(f"🔌 Disconnected from room: {self.room_name}")


# --- Utility functions ---
async def start_video_processor(interview_id_: PydanticObjectId, room_name: str):
    interview_id = str(interview_id_)
    if interview_id not in active_processors:
        processor = LiveKitVideoProcessor(interview_id, room_name)
        active_processors[interview_id] = processor
        asyncio.create_task(processor.connect())
        print(f"🚀 Started video processor for interview {interview_id}")


async def stop_video_processor(interview_id_: PydanticObjectId):
    interview_id = str(interview_id_)
    if interview_id in active_processors:
        processor = active_processors[interview_id]
        await processor.disconnect()
        del active_processors[interview_id]
        print(f"🛑 Stopped video processor for interview {interview_id}")


def get_integrity_score(interview_id_: PydanticObjectId):
    """Get current integrity score for an active interview."""
    interview_id = str(interview_id_)
    if interview_id in active_processors:
        processor = active_processors[interview_id]
        return processor.get_integrity_score()
    # FIX: if proctoring was already stopped (the /proc socket left first),
    # use the final score it saved on the way out instead of returning None.
    return active_sessions.get(interview_id, {}).get("final_integrity_score")


def get_detailed_integrity_report(interview_id_: PydanticObjectId):
    """Get detailed integrity report for an active interview."""
    interview_id = str(interview_id_)
    if interview_id in active_processors:
        processor = active_processors[interview_id]
        return processor.get_detailed_integrity_report()
    return active_sessions.get(interview_id, {}).get("detailed_integrity_report")
