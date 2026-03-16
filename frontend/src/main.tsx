import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

try {
  ReactDOM.createRoot(root).render(
    <React.StrictMode>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </React.StrictMode>,
  );
} catch (error) {
  const message = error instanceof Error ? error.message : "Unknown startup error";
  root.innerHTML = `
    <div style="font-family: Segoe UI, sans-serif; padding: 24px; color: #18212f;">
      <h1 style="margin-bottom: 12px;">ISBN Library</h1>
      <p style="margin-bottom: 8px;">アプリの初期化に失敗しました。</p>
      <pre style="white-space: pre-wrap; background: #f6fafc; padding: 12px; border-radius: 12px;">${message}</pre>
    </div>
  `;
}
