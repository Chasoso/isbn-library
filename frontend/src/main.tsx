import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles.css";

class AppErrorBoundary extends React.Component<
  React.PropsWithChildren,
  { hasError: boolean; message: string }
> {
  constructor(props: React.PropsWithChildren) {
    super(props);
    this.state = {
      hasError: false,
      message: "",
    };
  }

  static getDerivedStateFromError(error: Error) {
    return {
      hasError: true,
      message: error.message,
    };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="page-shell">
          <div className="card">
            <h1>ISBN Library</h1>
            <p>画面表示中にエラーが発生しました。</p>
            <p className="muted">{this.state.message}</p>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root element not found");
}

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <AppErrorBoundary>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </AppErrorBoundary>
  </React.StrictMode>,
);
