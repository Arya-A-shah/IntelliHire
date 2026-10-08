import React, { useEffect, useRef, useState } from "react";
import { useLocalParticipant } from "@livekit/components-react";
import { Track } from "livekit-client";

const LocalVideoPreview = () => {
  const { localParticipant } = useLocalParticipant();
  const videoRef = useRef(null);
  const [hasVideo, setHasVideo] = useState(false);

  useEffect(() => {
    if (!localParticipant || !videoRef.current) {
      return;
    }

    let isMounted = true;

    const attachVideoTrack = async () => {
      try {
        // Wait a bit for tracks to be published
        await new Promise((resolve) => setTimeout(resolve, 500));

        if (!isMounted) return;

        // Get video tracks
        const videoTracks = Array.from(
          localParticipant.videoTrackPublications?.values() || []
        );

        console.log("Video tracks:", videoTracks);

        // Find camera track
        const cameraTrackPublication = videoTracks.find(
          (pub) =>
            pub.source === Track.Source.Camera || pub.kind === Track.Kind.Video
        );

        if (cameraTrackPublication && cameraTrackPublication.track) {
          const mediaStreamTrack =
            cameraTrackPublication.track.mediaStreamTrack;

          if (mediaStreamTrack && videoRef.current) {
            const stream = new MediaStream([mediaStreamTrack]);
            videoRef.current.srcObject = stream;
            videoRef.current.play().catch((e) => {
              console.error("Error playing video:", e);
            });
            setHasVideo(true);
            console.log("Video track attached successfully");
          }
        } else {
          console.log("No camera track found yet, retrying...");
          // Retry after a delay
          setTimeout(attachVideoTrack, 1000);
        }
      } catch (error) {
        console.error("Error attaching video track:", error);
        // Retry on error
        if (isMounted) {
          setTimeout(attachVideoTrack, 1000);
        }
      }
    };

    attachVideoTrack();

    // Cleanup
    return () => {
      isMounted = false;
      if (videoRef.current) {
        videoRef.current.srcObject = null;
      }
    };
  }, [localParticipant]);

  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-950">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className={`w-full h-full object-cover ${
          hasVideo ? "opacity-100" : "opacity-0"
        }`}
      />

      {!hasVideo && (
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="animate-pulse mb-4">
            <svg
              className="w-16 h-16 text-gray-600"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
              />
            </svg>
          </div>
          <p className="text-gray-400">Initializing camera...</p>
        </div>
      )}
    </div>
  );
};

export default LocalVideoPreview;
