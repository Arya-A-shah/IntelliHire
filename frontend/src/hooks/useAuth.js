import { useMutation } from "@tanstack/react-query";
import { loginApi, signupApi } from "@/lib/api/auth";
import { useAuthStore } from "@/store/useAuthStore";

export function useLogin() {
  const setToken = useAuthStore((s) => s.setToken);

  const mutation = useMutation({
    mutationFn: loginApi,
    onSuccess: (res) => {
      setToken(res.access_token);
    },
  });

  return {
    login: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}

export function useSignup() {
  const setToken = useAuthStore((s) => s.setToken);

  const mutation = useMutation({
    mutationFn: signupApi,
    onSuccess: (res) => {
      setToken(res.access_token);
    },
  });

  return {
    signup: mutation.mutateAsync,
    isLoading: mutation.isPending,
    error: mutation.error,
  };
}
