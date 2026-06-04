import { Component } from "react";
import { TriangleAlert, RotateCcw } from "lucide-react";

/** Last-resort guard so a render error in any view degrades to a readable
 *  notice instead of a blank screen. Errors are still logged to the console
 *  (not swallowed) so they remain debuggable. */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { error: null };
  }

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error, info) {
    // Keep the full trace visible for debugging — do not swallow.
    console.error("UI crashed:", error, info?.componentStack);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
        <TriangleAlert size={36} className="text-signal-red" />
        <div>
          <h1 className="font-serif text-xl font-bold text-white">Something went wrong</h1>
          <p className="mt-1 max-w-md text-sm text-slate-400">
            The interface hit an unexpected error and could not render. Reloading
            usually clears it; if it persists, please report it.
          </p>
        </div>
        <code className="max-w-md break-words rounded-lg bg-ink-900/70 px-3 py-2 text-xs text-slate-500">
          {String(this.state.error?.message || this.state.error)}
        </code>
        <button
          onClick={() => window.location.reload()}
          className="inline-flex items-center gap-2 rounded-lg bg-accent-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-accent-700"
        >
          <RotateCcw size={15} /> Reload
        </button>
      </div>
    );
  }
}
