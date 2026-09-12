// Khi deploy public, set VITE_API_BASE_URL trên Vercel/Netlify thành URL backend thật
// (vd. https://edumind-ai-backend.onrender.com). Local dev không cần set gì, mặc định
// trỏ vào backend chạy trên máy.
export const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8123";

export async function uploadDocument(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE_URL}/documents/upload`, { method: "POST", body: form });
  if (!res.ok) throw new Error((await res.json()).detail || "Upload thất bại");
  return res.json();
}

export async function processDocument(docId) {
  const res = await fetch(`${BASE_URL}/documents/${docId}/process`, { method: "POST" });
  if (!res.ok) throw new Error((await res.json()).detail || "Xử lý thất bại");
  return res.json();
}

export async function askQuestion(docId, question) {
  const res = await fetch(`${BASE_URL}/documents/${docId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error((await res.json()).detail || "Hỏi thất bại");
  return res.json();
}
