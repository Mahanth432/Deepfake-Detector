import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL?.trim() || "http://localhost:8000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
});

export function getStoredUser() {
  try {
    const raw = localStorage.getItem("deepfake_user");
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  localStorage.setItem("deepfake_user", JSON.stringify(user));
}

export function clearStoredUser() {
  localStorage.removeItem("deepfake_user");
}

export function getDisplayConfidence(prediction, confidenceScore) {
  const score = Number(confidenceScore ?? 0);
  if ((prediction || "").toLowerCase() === "real") {
    return (1 - score) * 100;
  }
  return score * 100;
}

export async function predictImage(file) {
  const formData = new FormData();
  formData.append("file", file);
  const user = getStoredUser();
  formData.append("user_email", user?.email || "");
  const { data } = await api.post("/predict-image", formData);
  return data;
}

export async function getHistory(limit = 20) {
  const user = getStoredUser();
  const params = { limit };
  if (user?.email) params.email = user.email;
  const { data } = await api.get("/history", { params });
  return data;
}

export async function login(payload) {
  const { data } = await api.post("/login", payload);
  return data;
}

export async function register(payload) {
  const { data } = await api.post("/register", payload);
  return data;
}

export async function sendRegisterOtp(payload) {
  const { data } = await api.post("/send-register-otp", payload);
  return data;
}

export async function verifyRegisterOtp(payload) {
  const { data } = await api.post("/verify-register-otp", payload);
  return data;
}

export async function forgotPassword(payload) {
  const { data } = await api.post("/forgot-password", payload);
  return data;
}

export async function verifyResetOtp(payload) {
  const { data } = await api.post("/verify-reset-otp", payload);
  return data;
}

export async function resetPassword(payload) {
  const { data } = await api.post("/reset-password", payload);
  return data;
}

export default api;
