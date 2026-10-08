import { useEffect, useState } from "react";
import { io } from "socket.io-client";
import { Link, useParams } from "react-router";
import Interview from "../components/Interview";
import { Proctoring } from "@/components/Proctoring";
import { useSocketStore } from "@/store/useSocketStore";
import { useAuthStore } from "@/store/useAuthStore";
import { API_URL } from "@/lib/api/config";

export default function InterviewScreen() {
  const { interviewId } = useParams();
  const { setAIConnected, setSignalingConnected } = useSocketStore();
  const token = useAuthStore((s) => s.token);

  // LiveKit credentials from /interviews/start. FIX: Proctoring used to call
  // /start a second time on its own; now this page calls it once and passes
  // the result down as props.
  const [livekit, setLivekit] = useState(null); // { token, url }
  const [error, setError] = useState(null);
  const [aiSocket, setAISocket] = useState(null);
  const [signalingSocket, setSignalingSocket] = useState(null);

  // Step 1: start the interview session (once per interview id)
  useEffect(() => {
    let cancelled = false; // ignore the answer if we left the page meanwhile

    const startSession = async () => {
      try {
        const res = await fetch(`${API_URL}/interviews/start/${interviewId}`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.detail || `Could not start interview (${res.status})`);
        }
        if (!cancelled) setLivekit({ token: data.token, url: data.url });
      } catch (err) {
        if (!cancelled) setError(err.message);
      }
    };

    startSession();
    return () => {
      cancelled = true;
    };
  }, [interviewId, token]);

  // Step 2: open both sockets once the session exists
  useEffect(() => {
    if (!livekit) return;

    const options = {
      transports: ["websocket"],
      auth: { token },
      query: { interview_id: interviewId },
    };
    const ai = io(`${API_URL}/ai`, options);
    const signaling = io(`${API_URL}/proc`, options);

    ai.on("connect", () => setAIConnected(true));
    ai.on("disconnect", () => setAIConnected(false));
    // FIX: the server now refuses with a reason (e.g. "questions are still
    // being prepared"). Show it instead of an endless spinner.
    ai.on("connect_error", (err) => setError(err.message));

    signaling.on("connect", () => setSignalingConnected(true));
    signaling.on("disconnect", () => setSignalingConnected(false));

    setAISocket(ai);
    setSignalingSocket(signaling);

    // FIX: this cleanup used to be returned from inside a setTimeout callback.
    // React only sees what the effect itself returns, so the sockets were
    // never closed when you left the page (they kept running in the background).
    return () => {
      ai.disconnect();
      signaling.disconnect();
      setAIConnected(false);
      setSignalingConnected(false);
      setAISocket(null);
      setSignalingSocket(null);
    };
  }, [livekit, interviewId, token, setAIConnected, setSignalingConnected]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-white p-6">
        <div className="text-center max-w-md">
          <p className="text-lg font-semibold mb-2">Can't start the interview</p>
          <p className="text-sm text-gray-300 mb-6">{error}</p>
          <Link to="/dashboard" className="underline text-sm">
            Back to dashboard
          </Link>
        </div>
      </div>
    );
  }

  if (!livekit || !aiSocket || !signalingSocket) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900 text-white">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white mx-auto mb-4"></div>
          <p className="text-lg">Initializing interview session...</p>
          <p className="text-sm text-gray-400 mt-2">
            {!livekit ? "Creating session..." : "Connecting..."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col lg:flex-row h-screen bg-gray-100">
      <div className="flex-1 border-r border-gray-200 overflow-hidden">
        <Interview aiSocket={aiSocket} />
      </div>
      <div className="flex-1 overflow-y-auto bg-gray-50">
        <Proctoring
          signalingSocket={signalingSocket}
          interviewId={interviewId}
          livekitToken={livekit.token}
          livekitUrl={livekit.url}
        />
      </div>
    </div>
  );
}
