import { Component, type ErrorInfo, type ReactNode } from "react"

export class RouteErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error("Page rendering failed", error, info.componentStack) }
  render() {
    if (!this.state.failed) return this.props.children
    return <main role="alert" className="p-8 text-ui-primary bg-ui-bg">
      <p>This page could not be displayed.</p>
      <button onClick={() => window.location.reload()}>Reload page</button>
    </main>
  }
}
