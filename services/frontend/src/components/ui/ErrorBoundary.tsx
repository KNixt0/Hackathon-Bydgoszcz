import { Component, type ReactNode } from "react";
import { ErrorState } from "./States";

interface Props {
  children: ReactNode;
}
interface State {
  failed: boolean;
}

/** Last line of defence: a render error shows a recoverable screen instead of a blank page. */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch() {
    // Intentionally silent: the failure is rendered for the user, nothing is written to the console.
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <div style={{ maxWidth: 560, margin: "12vh auto" }}>
        <ErrorState
          title="Widok nie mógł zostać wyświetlony"
          message="Wystąpił nieoczekiwany błąd interfejsu. Dane spraw nie zostały zmienione."
          onRetry={() => window.location.reload()}
        />
      </div>
    );
  }
}
