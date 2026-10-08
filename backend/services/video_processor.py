import cv2
import mediapipe as mp
import numpy as np

mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh

face_detector = mp_face_detection.FaceDetection(model_selection=0, min_detection_confidence=0.5)
face_mesh = mp_face_mesh.FaceMesh(
    refine_landmarks=True,
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)


def calculate_eye_aspect_ratio(eye_landmarks, landmarks):
    """Calculate Eye Aspect Ratio (EAR) for eye closure detection."""
    try:
        # Vertical eye distances
        v1 = np.linalg.norm(
            np.array([landmarks[eye_landmarks[1]].x, landmarks[eye_landmarks[1]].y]) - 
            np.array([landmarks[eye_landmarks[5]].x, landmarks[eye_landmarks[5]].y])
        )
        v2 = np.linalg.norm(
            np.array([landmarks[eye_landmarks[2]].x, landmarks[eye_landmarks[2]].y]) - 
            np.array([landmarks[eye_landmarks[4]].x, landmarks[eye_landmarks[4]].y])
        )
        
        # Horizontal eye distance
        h = np.linalg.norm(
            np.array([landmarks[eye_landmarks[0]].x, landmarks[eye_landmarks[0]].y]) - 
            np.array([landmarks[eye_landmarks[3]].x, landmarks[eye_landmarks[3]].y])
        )
        
        if h == 0:
            return 0.3
        
        ear = (v1 + v2) / (2.0 * h)
        return ear
    except:
        return 0.3


def calculate_head_pose(landmarks, frame_width, frame_height):
    """Calculate head orientation angles with improved accuracy."""
    try:
        # Key facial landmarks for pose estimation
        nose_tip = landmarks[1]
        chin = landmarks[152]
        left_eye_corner = landmarks[33]
        right_eye_corner = landmarks[263]
        left_mouth = landmarks[61]
        right_mouth = landmarks[291]
        
        # 2D image points
        image_points = np.array([
            (nose_tip.x * frame_width, nose_tip.y * frame_height),
            (chin.x * frame_width, chin.y * frame_height),
            (left_eye_corner.x * frame_width, left_eye_corner.y * frame_height),
            (right_eye_corner.x * frame_width, right_eye_corner.y * frame_height),
            (left_mouth.x * frame_width, left_mouth.y * frame_height),
            (right_mouth.x * frame_width, right_mouth.y * frame_height)
        ], dtype="double")
        
        # 3D model points
        model_points = np.array([
            (0.0, 0.0, 0.0),
            (0.0, -330.0, -65.0),
            (-225.0, 170.0, -135.0),
            (225.0, 170.0, -135.0),
            (-150.0, -150.0, -125.0),
            (150.0, -150.0, -125.0)
        ])
        
        # Camera matrix
        focal_length = frame_width
        center = (frame_width / 2, frame_height / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")
        
        dist_coeffs = np.zeros((4, 1))
        
        # Solve for pose
        success, rotation_vec, translation_vec = cv2.solvePnP(
            model_points, image_points, camera_matrix, dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE
        )
        
        if not success:
            return 0.0, 0.0, 0.0
        
        # Convert rotation vector to matrix
        rotation_matrix, _ = cv2.Rodrigues(rotation_vec)
        
        # Extract Euler angles
        pose_mat = cv2.hconcat((rotation_matrix, translation_vec))
        _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)
        
        pitch = float(euler_angles[0][0])
        yaw = float(euler_angles[1][0])
        roll = float(euler_angles[2][0])
        
        return pitch, yaw, roll
        
    except Exception as e:
        return 0.0, 0.0, 0.0


def get_gaze_direction(landmarks):
    """Estimate gaze direction using iris positions."""
    try:
        # Left eye
        left_eye_left = landmarks[33]
        left_eye_right = landmarks[133]
        left_iris = landmarks[468]
        
        # Right eye
        right_eye_left = landmarks[362]
        right_eye_right = landmarks[263]
        right_iris = landmarks[473]
        
        # Calculate horizontal gaze ratio
        left_eye_width = abs(left_eye_right.x - left_eye_left.x)
        left_iris_pos = abs(left_iris.x - left_eye_left.x)
        left_gaze_ratio = left_iris_pos / left_eye_width if left_eye_width > 0 else 0.5
        
        right_eye_width = abs(right_eye_right.x - right_eye_left.x)
        right_iris_pos = abs(right_iris.x - right_eye_left.x)
        right_gaze_ratio = right_iris_pos / right_eye_width if right_eye_width > 0 else 0.5
        
        avg_gaze_ratio = (left_gaze_ratio + right_gaze_ratio) / 2.0
        return avg_gaze_ratio
        
    except:
        return 0.5


def analyze_frame(frame):
    """
    Analyze video frame for proctoring with improved accuracy.
    
    Detection Strategy:
    - Uses stricter thresholds to reduce false positives
    - Focuses on clear suspicious behaviors
    - Ignores minor movements to avoid spam
    
    Returns list of detected events.
    """
    if frame is None or frame.size == 0:
        return []
    
    h, w = frame.shape[:2]
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    detections = face_detector.process(rgb)
    mesh_results = face_mesh.process(rgb)
    
    events = []
    
    # === FACE DETECTION ===
    if not detections.detections:
        return ["no_face_detected"]
    
    if len(detections.detections) > 1:
        return ["multiple_faces_detected"]
    
    # === FACE MESH ANALYSIS ===
    if not mesh_results.multi_face_landmarks:
        return ["no_face_detected"]
    
    lm = mesh_results.multi_face_landmarks[0].landmark
    
    # === HEAD POSE ANALYSIS (IMPROVED THRESHOLDS) ===
    pitch, yaw, roll = calculate_head_pose(lm, w, h)
    
    # More strict yaw detection - only flag significant turns
    if abs(yaw) > 35:
        if yaw > 0:
            events.append("looking_right")
        else:
            events.append("looking_left")
    
    # Pitch detection - looking up or down significantly
    # if pitch < -25:  # Looking up
    #     events.append("looking_up")
    # elif pitch > 30:  # Looking down
    #     events.append("looking_down")
    
    # Extreme roll - unusual head tilt
    if abs(roll) > 40:
        events.append("head_tilted")
    
    # === EYE CLOSURE DETECTION ===
    left_eye_indices = [33, 160, 158, 133, 153, 144]
    right_eye_indices = [362, 385, 387, 263, 373, 380]
    
    left_ear = calculate_eye_aspect_ratio(left_eye_indices, lm)
    right_ear = calculate_eye_aspect_ratio(right_eye_indices, lm)
    avg_ear = (left_ear + right_ear) / 2.0
    
    # Lower threshold for more accurate detection
    if avg_ear < 0.15:
        events.append("eyes_closed")
    
    # === GAZE DIRECTION (IMPROVED) ===
    gaze_ratio = get_gaze_direction(lm)
    
    # More strict gaze detection
    if gaze_ratio < 0.25:
        events.append("gaze_left")
    elif gaze_ratio > 0.75:
        events.append("gaze_right")
    
    # === MOUTH MOVEMENT (TALKING) ===
    upper_lip = lm[13]
    lower_lip = lm[14]
    
    # Vertical mouth opening
    mouth_height = abs(upper_lip.y - lower_lip.y)
    
    # Higher threshold to avoid false positives
    if mouth_height > 0.05:
        events.append("talking")
    
    # === DISTANCE CHECKS ===
    face_width = abs(lm[454].x - lm[234].x)
    
    if face_width > 0.65:  # Face very close
        events.append("face_too_close")
    elif face_width < 0.20:  # Face very far
        events.append("face_too_far")
    
    # === FACE POSITIONING ===
    nose_x = lm[1].x
    nose_y = lm[1].y
    
    # Check if face is significantly off-center
    if nose_x < 0.25 or nose_x > 0.75 or nose_y < 0.15 or nose_y > 0.85:
        events.append("face_not_centered")
    
    return events