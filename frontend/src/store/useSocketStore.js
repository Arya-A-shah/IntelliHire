import { create } from "zustand";

export const useSocketStore = create((set) => ({
  aiConnected: false,
  signalingConnected: false,

  setAIConnected: (status) => set({ aiConnected: status }),
  setSignalingConnected: (status) => set({ signalingConnected: status }),
}));