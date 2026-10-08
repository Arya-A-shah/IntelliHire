import { create } from "zustand";
import { jwtDecode } from "jwt-decode";

function decodeToken(token) {
  if (!token) return null;

  try {
    const decoded = jwtDecode(token);

    if (decoded.exp && decoded.exp * 1000 < Date.now()) {
      localStorage.removeItem("token");
      return null;
    }

    return {
      id: decoded.user_id,
      name: decoded.name,
      email: decoded.email,
      role: decoded.role,
    };
  } catch (err) {
    console.error("Invalid token:", err);
    return null;
  }
}

export const useAuthStore = create((set) => {
  const storedToken = localStorage.getItem("token");
  const user = decodeToken(storedToken);

  return {
    // FIX: an expired token used to stay here even though decodeToken() had
    // already rejected it (user = null). ProtectedRoute saw a token and let
    // you in, but the dashboard had no user, so it showed "Loading..." forever.
    token: user ? storedToken : null,
    user,

    setToken: (token) => {
      if (token) {
        localStorage.setItem("token", token);
        const decodedUser = decodeToken(token);
        set({ token, user: decodedUser });
      } else {
        localStorage.removeItem("token");
        set({ token: null, user: null });
      }
    },

    logout: () => {
      localStorage.removeItem("token");
      set({ token: null, user: null });
    },

    isAuthenticated: () => {
      const token = localStorage.getItem("token");
      const user = decodeToken(token);
      return !!user;
    },
  };
});
