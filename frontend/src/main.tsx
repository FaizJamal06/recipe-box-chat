import { Component, StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import "./index.css";

/** A render bug shows a readable message instead of a blank page. */
class Boundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    const e = this.state.error;
    return e ? <div className="m-8 rounded-lg border border-bad/30 bg-bad-soft p-4 text-bad">
      <p className="font-semibold">Something broke while drawing this answer.</p>
      <pre className="mt-2 whitespace-pre-wrap font-mono text-xs">{e.message}{"\n"}{e.stack}</pre>
      <button className="mt-3 underline" onClick={() => location.assign("/")}>Start over</button></div> : this.props.children;
  }
}

createRoot(document.getElementById("root")!).render(<StrictMode><Boundary><App /></Boundary></StrictMode>);
