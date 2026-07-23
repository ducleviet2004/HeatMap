import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(
      "Application render failure",
      error.message,
      info.componentStack,
    );
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-error">
          <p className="eyebrow">APPLICATION ERROR</p>
          <h1>The status console could not render.</h1>
          <button onClick={() => window.location.reload()}>
            Reload console
          </button>
        </main>
      );
    }
    return this.props.children;
  }
}
