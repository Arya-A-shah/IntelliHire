import { useEffect, useState, useRef } from "react";
import { useSocketStore } from "@/store/useSocketStore";
import { useNavigate } from "react-router";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

export default function Interview({ aiSocket }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isListening, setIsListening] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [interimTranscript, setInterimTranscript] = useState("");
  const [isLeavingInterview, setIsLeavingInterview] = useState(false);
  const [showLeaveDialog, setShowLeaveDialog] = useState(false);
  const { aiConnected } = useSocketStore();
  const navigate = useNavigate();

  const emitAI = (event, data) => {
    if (aiSocket && aiSocket.connected) aiSocket.emit(event, data);
    else console.warn("[emitAI] socket not connected:", event);
  };

  const recognitionRef = useRef(null);
  const messagesEndRef = useRef(null);
  const finalTranscriptRef = useRef("");

  // keep a ref mirror for isListening for reliable checks in callbacks
  const isListeningRef = useRef(false);

  // to track whether we should resume STT after AI audio finishes
  const shouldResumeAfterAudioRef = useRef(false);

  // Web Audio API refs
  const audioCtxRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isAudioPlayingRef = useRef(false);
  const nextAudioTimeRef = useRef(0);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    if (!audioCtxRef.current) {
      audioCtxRef.current = new (window.AudioContext ||
        window.webkitAudioContext)();
    }
  }, []);

  // --- Correct base64 -> Float32 decoding (assumes encoded as raw float32 bytes) ---
  const base64ToFloat32 = (b64) => {
    // decode base64 to binary string
    const binary = atob(b64);
    // create buffer and fill with byte values
    const buffer = new ArrayBuffer(binary.length);
    const bytes = new Uint8Array(buffer);
    for (let i = 0; i < binary.length; i++) {
      bytes[i] = binary.charCodeAt(i) & 0xff;
    }
    // interpret buffer as Float32Array (little-endian as typical)
    return new Float32Array(buffer);
  };

  const playAudioChunk = (pcmB64, sampleRate = 16000) => {
    const floatArray = base64ToFloat32(pcmB64);
    const audioCtx = audioCtxRef.current;
    if (!audioCtx) return;

    // Pause recognition if currently listening to avoid microphone/playback conflicts
    if (isListeningRef.current && recognitionRef.current) {
      try {
        recognitionRef.current.stop();
        shouldResumeAfterAudioRef.current = true;
        // set state refs
        setIsListening(false);
        isListeningRef.current = false;
      } catch (e) {
        console.warn("Could not stop recognition before playback:", e);
      }
    }

    // Create an AudioBuffer with the decoded float data
    const buffer = audioCtx.createBuffer(1, floatArray.length, sampleRate);
    buffer.copyToChannel(floatArray, 0);

    audioQueueRef.current.push(buffer);
    if (!isAudioPlayingRef.current) playQueue();
  };

  const playQueue = () => {
    const audioCtx = audioCtxRef.current;
    if (!audioCtx) return;

    if (audioQueueRef.current.length === 0) {
      isAudioPlayingRef.current = false;
      setIsAudioPlaying(false);
      // If we stopped because of playback and the user was listening before,
      // resume recognition.
      if (shouldResumeAfterAudioRef.current) {
        shouldResumeAfterAudioRef.current = false;
        // small timeout ensures audio device freed
        setTimeout(() => {
          // Only auto-restart if user had previously requested listening
          startListening({ automatic: true });
        }, 150);
      }
      return;
    }

    isAudioPlayingRef.current = true;
    setIsAudioPlaying(true);

    const buffer = audioQueueRef.current.shift();
    const source = audioCtx.createBufferSource();
    source.buffer = buffer;
    source.connect(audioCtx.destination);

    const currentTime = audioCtx.currentTime;
    const startTime = Math.max(
      nextAudioTimeRef.current || currentTime,
      currentTime
    );
    nextAudioTimeRef.current = startTime + buffer.duration;

    source.onended = () => {
      // call recursively to play next chunk
      playQueue();
    };

    // Start playing at calculated time
    try {
      source.start(startTime);
    } catch (e) {
      console.error("Audio start error:", e);
      // fallback: immediate start
      try {
        source.start();
      } catch (err2) {
        console.error("Fallback audio start failed:", err2);
        // clear queue to avoid endless loops
        audioQueueRef.current = [];
        isAudioPlayingRef.current = false;
        setIsAudioPlaying(false);
      }
    }
  };

  // --- Speech recognition setup ---
  const initializeSpeechRecognition = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      recognitionRef.current = null;
      return;
    }
    setSpeechSupported(true);

    // if already created, skip
    if (recognitionRef.current) return;

    const rec = new SpeechRecognition();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onstart = () => {
      setIsListening(true);
      isListeningRef.current = true;
      finalTranscriptRef.current = "";
      setInterimTranscript("");
    };

    rec.onresult = (event) => {
      let interim = "";
      let finalPart = "";
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const r = event.results[i];
        if (r.isFinal) finalPart += r[0].transcript;
        else interim += r[0].transcript;
      }
      if (finalPart) finalTranscriptRef.current += finalPart;
      setInterimTranscript(interim);
      setInput((finalTranscriptRef.current + " " + interim).trim());
    };

    rec.onerror = (e) => {
      console.error("Speech recognition error:", e);
      // On some errors, recognition stops — ensure state cleanup
      setIsListening(false);
      isListeningRef.current = false;
      // don't throw; allow user to restart
    };

    rec.onend = () => {
      // If we intentionally stopped to play audio, don't auto-restart here.
      setIsListening(false);
      isListeningRef.current = false;

      // If recognition ended unexpectedly but we still want continuous behavior,
      // and the user had requested listening, try to restart (with a tiny delay).
      // We avoid infinite loops by checking shouldResumeAfterAudioRef (which is handled elsewhere).
      // If the user toggled listening off intentionally, we won't restart.
      // If recognitionRef is present and speechSupported and the user had clicked listen,
      // we will not automatically restart unless startListening was called by user.
    };

    recognitionRef.current = rec;
  };

  // startListening optionally accepts { automatic } meaning it's an auto-resume after audio
  const startListening = async ({ automatic = false } = {}) => {
    if (!speechSupported) {
      // initialize once more attempt
      initializeSpeechRecognition();
      if (!speechSupported) {
        console.warn("SpeechRecognition not supported in this browser.");
        return;
      }
    }

    // If recognition has not been created (rare), create it
    if (!recognitionRef.current) initializeSpeechRecognition();

    // If already listening, stop
    if (isListeningRef.current) {
      stopListening();
      return;
    }

    // For automatic resumes after playback, only resume if user had previously started listening.
    if (automatic && !shouldResumeAfterAudioRef.current) {
      // do not auto-start if not flagged
      return;
    }

    // Ensure audio context is resumed on user gesture
    try {
      if (audioCtxRef.current && audioCtxRef.current.state === "suspended") {
        await audioCtxRef.current.resume();
      }
    } catch (e) {
      // ignore
    }

    try {
      recognitionRef.current.start();
      // update refs/states immediately — the onstart handler will also set them
      isListeningRef.current = true;
      setIsListening(true);
    } catch (err) {
      console.error("startListening failed:", err);
      // Some browsers require a user gesture to start; ensure this is called via a user click.
    }
  };

  const stopListening = () => {
    try {
      recognitionRef.current?.stop();
    } catch (err) {
      console.error("stopListening error:", err);
    } finally {
      setIsListening(false);
      isListeningRef.current = false;
      shouldResumeAfterAudioRef.current = false;
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const sendMessage = () => {
    if (!input.trim() || !aiConnected) return;
    emitAI("user_message", input.trim());
    setMessages((p) => [
      ...p,
      {
        id: `user-${Date.now()}`,
        from: "user",
        text: input.trim(),
        timestamp: Date.now(),
      },
    ]);
    setInput("");
    // if listening, keep it running; user typed a message so no special handling
  };

  // --- Leave Interview Modal ---
  const handleConfirmLeave = () => {
    if (!aiConnected) {
      console.warn("[Leave Interview] AI socket not connected");
      return;
    }

    setIsLeavingInterview(true);
    console.log("[Leave Interview] Emitting leave_interview event");

    if (isListeningRef.current) stopListening();

    emitAI("leave_interview");

    setMessages((p) => [
      ...p,
      {
        id: `system-${Date.now()}`,
        from: "system",
        text: "Leaving interview... Generating your report.",
        timestamp: Date.now(),
      },
    ]);

    setShowLeaveDialog(false);
    // Navigate to dashboard after a short delay
    setTimeout(() => {
      navigate("/dashboard");
    }, 1000);
  };

  // --- AI Socket listeners ---
  useEffect(() => {
    // initialize on mount (not only when aiSocket connects) so mic can be started immediately by user
    initializeSpeechRecognition();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // run once

  useEffect(() => {
    if (!aiSocket) return;

    aiSocket.off("ai_partial");
    aiSocket.off("ai_audio_blob");
    aiSocket.off("ai_streaming_complete");
    aiSocket.off("ai_error");

    aiSocket.on("ai_partial", (data) => {
      const text = typeof data === "string" ? data : data.text;
      const messageId = typeof data === "object" ? data.message_id : null;
      const cleaned = text?.trim();
      if (!cleaned) return;

      setMessages((prev) => {
        const updated = [...prev];
        const existingIdx = updated.findIndex(
          (m) => m.from === "ai" && m.message_id === messageId
        );

        if (existingIdx !== -1) {
          updated[existingIdx].text += " " + cleaned;
          return updated;
        } else {
          return [
            ...updated,
            {
              id: `ai-${messageId}-${Date.now()}`,
              message_id: messageId,
              from: "ai",
              text: cleaned,
              timestamp: Date.now(),
            },
          ];
        }
      });
    });

    aiSocket.on("ai_audio_blob", (data) => {
      if (!data?.audio) return;
      // playAudioChunk will handle pausing/restarting recognition if needed
      playAudioChunk(data.audio, data.sample_rate || 48000);
    });

    aiSocket.on("ai_error", (data) => {
      const errorText = typeof data === "string" ? data : data.error;
      setMessages((p) => [
        ...p,
        {
          id: `error-${Date.now()}`,
          from: "system",
          text: `Error: ${errorText}`,
          timestamp: Date.now(),
          isError: true,
        },
      ]);
    });

    // FIX: the server now says when the interview is over (after the last
    // question) and then closes the socket. Before, the page just sat there.
    aiSocket.on("interview_ended", () => {
      stopListening();
      setMessages((p) => [
        ...p,
        {
          id: `system-${Date.now()}`,
          from: "system",
          text: "Interview complete. Your report is being generated. Returning to your dashboard...",
          timestamp: Date.now(),
        },
      ]);
      setTimeout(() => navigate("/dashboard"), 4000);
    });

    // Ensure recognizer exists if socket connects later
    initializeSpeechRecognition();

    return () => {
      try {
        recognitionRef.current?.stop();
      } catch (e) {
        // ignore
      }
      audioQueueRef.current = [];
      aiSocket.off("ai_partial");
      aiSocket.off("ai_audio_blob");
      aiSocket.off("ai_streaming_complete");
      aiSocket.off("ai_error");
      aiSocket.off("interview_ended");
    };
  }, [aiSocket]);

  return (
    <>
      {/* Leave Interview Modal */}
      <Dialog open={showLeaveDialog} onOpenChange={setShowLeaveDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Leave Interview</DialogTitle>
            <DialogDescription>
              Are you sure you want to leave the interview? Your responses will
              be saved and your report will be generated automatically.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setShowLeaveDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleConfirmLeave}
              disabled={isLeavingInterview}
            >
              {isLeavingInterview ? "Leaving..." : "Confirm"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <div className="flex flex-col h-screen max-w-4xl mx-auto p-4 bg-gray-50">
        <div className="mb-4 p-4 bg-white rounded-lg shadow">
          <div className="flex items-center justify-between">
            <h1 className="text-2xl font-bold text-gray-800">
              AI Interview Assistant
            </h1>

            <Button
              onClick={() => setShowLeaveDialog(true)}
              disabled={!aiConnected || isLeavingInterview}
              variant="destructive"
              className="font-medium"
            >
              {isLeavingInterview ? "Leaving..." : "Leave Interview"}
            </Button>
          </div>

          <div className="mt-2 flex items-center gap-4 flex-wrap text-sm">
            <div
              className={`flex items-center gap-2 ${
                aiConnected ? "text-green-600" : "text-red-600"
              }`}
            >
              <div
                className={`w-3 h-3 rounded-full ${
                  aiConnected ? "bg-green-500" : "bg-red-500"
                }`}
              ></div>
              {aiConnected ? "Connected" : "Disconnected"}
            </div>

            <div className="ml-4 text-sm">
              STT:{" "}
              <span
                className={speechSupported ? "text-green-600" : "text-red-600"}
              >
                {speechSupported ? "Supported" : "Not supported"}
              </span>
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="flex-1 bg-white rounded-lg shadow overflow-hidden flex flex-col">
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`flex ${
                  m.from === "user" ? "justify-end" : "justify-start"
                }`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                    m.from === "user"
                      ? "bg-blue-500 text-white"
                      : m.isError
                      ? "bg-red-100 text-red-700 border border-red-300"
                      : m.from === "system"
                      ? "bg-gray-100 text-gray-700"
                      : "bg-gray-200 text-gray-800"
                  }`}
                >
                  <div className="text-xs opacity-75 mb-1 capitalize font-medium">
                    {m.from === "ai" ? "Interviewer" : m.from}
                  </div>
                  <div className="text-sm whitespace-pre-line">{m.text}</div>
                </div>
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Section */}
          <div className="border-t bg-gray-50 p-4">
            <div className="flex gap-2 items-end">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type or speak your response..."
                className="flex-1 p-3 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 text-zinc-950"
                rows="2"
                // allow typing while listening; only block when leaving or disconnected
                disabled={!aiConnected || isLeavingInterview}
              />
              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  <Button
                    onClick={() => startListening()}
                    disabled={
                      !speechSupported || isLeavingInterview || !aiConnected
                    }
                  >
                    {isListening ? "Stop Mic" : "Start Mic"}
                  </Button>
                  <Button
                    onClick={sendMessage}
                    disabled={
                      !input.trim() || !aiConnected || isLeavingInterview
                    }
                  >
                    Send
                  </Button>
                </div>
                <div className="text-xs text-zinc-600">
                  {isListening
                    ? "Listening..."
                    : isAudioPlaying
                    ? "Playing audio..."
                    : interimTranscript
                    ? `Interim: ${interimTranscript}`
                    : ""}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
