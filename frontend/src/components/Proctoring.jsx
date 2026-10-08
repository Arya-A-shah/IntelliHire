import React, { useEffect, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  ControlBar,
} from "@livekit/components-react";
import "@livekit/components-styles";
import LocalVideoPreview from "./LocalVideoPreview";

// FIX: token and url now come from InterviewScreen, which already called
// /interviews/start. This component used to call it a second time, which
// minted a second LiveKit token and reset the server's session.
export const Proctoring = ({
  signalingSocket,
  interviewId,
  livekitToken: token,
  livekitUrl: url,
}) => {
  const [events, setEvents] = useState([]);
  const [connectedToRoom, setConnectedToRoom] = useState(false);
  const [procSocketConnected, setProcSocketConnected] = useState(false);

  useEffect(() => {
    if (!signalingSocket) {
      console.log("⚠️ Waiting for signaling socket...");
      return;
    }

    console.log("🔌 Setting up socket listeners for interview:", interviewId);

    // Event handlers
    const handleAnalysis = (data) => {
      console.log("📨 Received analysis_events:", data);

      if (data?.interview_id !== interviewId) {
        console.log("⚠️ Event for different interview, ignoring");
        return;
      }

      if (data.events && Array.isArray(data.events)) {
        console.log("✅ Adding events to state:", data.events);
        setEvents((prev) => {
          const newEvents = [
            ...prev,
            ...data.events.map((evt) => ({
              message: evt,
              timestamp: new Date().toLocaleTimeString(),
              frame_count: data.frame_count,
            })),
          ];
          console.log("📊 Total events now:", newEvents.length);
          return newEvents.slice(-200);
        });
      }
    };

    const handleParticipantJoined = (data) => {
      console.log("👤 Participant joined:", data);
      setEvents((prev) =>
        [
          ...prev,
          {
            message: `✅ ${data.participant} joined`,
            timestamp: new Date().toLocaleTimeString(),
          },
        ].slice(-200)
      );
    };

    const handleParticipantLeft = (data) => {
      console.log("👋 Participant left:", data);
      setEvents((prev) =>
        [
          ...prev,
          {
            message: `❌ ${data.participant} left`,
            timestamp: new Date().toLocaleTimeString(),
          },
        ].slice(-200)
      );
    };

    const handleJoinedInterview = (data) => {
      console.log("✅ Joined interview confirmed:", data);
      setProcSocketConnected(true);
      setEvents((prev) =>
        [
          ...prev,
          {
            message: data.message || "Connected to proctoring system",
            timestamp: new Date().toLocaleTimeString(),
          },
        ].slice(-200)
      );
    };

    const handleProcError = (data) => {
      console.error("❌ Proctoring socket error:", data);
      setProcSocketConnected(false);
      setEvents((prev) =>
        [
          ...prev,
          {
            message: `🚨 Error: ${data.error}`,
            timestamp: new Date().toLocaleTimeString(),
          },
        ].slice(-200)
      );
    };

    const handleDisconnect = () => {
      console.log("🔌 Proctoring socket disconnected");
      setProcSocketConnected(false);
    };

    // Register all listeners
    signalingSocket.on("analysis_events", handleAnalysis);
    signalingSocket.on("participant_joined", handleParticipantJoined);
    signalingSocket.on("participant_left", handleParticipantLeft);
    signalingSocket.on("joined_interview", handleJoinedInterview);
    signalingSocket.on("proc_error", handleProcError);
    signalingSocket.on("disconnect", handleDisconnect);
    // The socket may have connected before this component mounted.
    if (signalingSocket.connected) setProcSocketConnected(true);

    return () => {
      console.log("🧹 Cleaning up socket listeners");

      signalingSocket.off("analysis_events", handleAnalysis);
      signalingSocket.off("participant_joined", handleParticipantJoined);
      signalingSocket.off("participant_left", handleParticipantLeft);
      signalingSocket.off("joined_interview", handleJoinedInterview);
      signalingSocket.off("proc_error", handleProcError);
      signalingSocket.off("disconnect", handleDisconnect);

      // Leave the room
      console.log("📡 Leaving interview room:", interviewId);
      signalingSocket.emit("leave_interview", { interview_id: interviewId });
    };
  }, [signalingSocket, interviewId]);

  if (!token || !url) {
    return (
      <div className="flex items-center justify-center h-full bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p>Loading video room...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full bg-gray-900 text-white">
      {/* Video preview */}
      <div className="flex-1 flex flex-col items-center justify-center p-4">
        <LiveKitRoom
          token={token}
          serverUrl={url}
          connect={true}
          video={true}
          audio={false}
          onConnected={() => {
            console.log("🎥 Connected to LiveKit room");
            setConnectedToRoom(true);
          }}
          onDisconnected={() => {
            console.log("🔌 Disconnected from LiveKit room");
            setConnectedToRoom(false);
          }}
          className="w-full h-full"
        >
          <div className="relative w-full h-full bg-black rounded-lg overflow-hidden">
            <LocalVideoPreview />
            <RoomAudioRenderer />
            <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10">
              <ControlBar
                variation="minimal"
                controls={{ microphone: false }}
              />
            </div>
          </div>
        </LiveKitRoom>
      </div>

      {/* Events panel */}
      <div className="w-full bg-gray-800 p-4 max-h-64 overflow-y-auto">
        <div className="flex items-center justify-between mb-3 pb-3 border-b border-gray-700">
          <h3 className="text-lg font-semibold">Proctoring Events</h3>
          <div className="flex items-center gap-2">
            <div
              className={`w-2 h-2 rounded-full animate-pulse ${
                procSocketConnected ? "bg-green-500" : "bg-red-500"
              }`}
            ></div>
            <span
              className={`text-sm ${
                procSocketConnected ? "text-green-500" : "text-red-500"
              }`}
            >
              {procSocketConnected ? "Live" : "Offline"}
            </span>
          </div>
        </div>

        {/* Event count badge */}
        <div className="mb-3 px-3 py-2 bg-gray-700 rounded-lg">
          <span className="text-sm text-gray-300">
            Total Events:{" "}
            <span className="font-bold text-white">{events.length}</span>
          </span>
        </div>

        {/* Events list */}
        <div className="space-y-2">
          {events.length === 0 ? (
            <div className="text-center py-4">
              <p className="text-gray-400 text-sm">No events detected yet</p>
              <p className="text-gray-500 text-xs mt-1">
                {procSocketConnected
                  ? "Monitoring in progress..."
                  : "Waiting for connection..."}
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              {events
                .slice()
                .reverse()
                .slice(0, 10)
                .map((evt, i) => (
                  <div
                    key={`${i}-${evt.timestamp}`}
                    className="bg-gray-700 p-2 rounded-lg text-sm"
                  >
                    <p className="text-gray-100">{evt.message}</p>
                    <span className="text-xs text-gray-400">
                      {evt.timestamp}
                    </span>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Proctoring;
