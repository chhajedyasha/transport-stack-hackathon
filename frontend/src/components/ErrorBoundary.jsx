import React from 'react';
import { AlertCircle, RefreshCw, Home } from 'lucide-react';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Keep error logging clean
  }

  handleReload = () => {
    window.location.reload();
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-transit-bg flex items-center justify-center p-4">
          <div className="max-w-md w-full bg-white border border-transit-border rounded-panel p-6 text-center space-y-4">
            <div className="w-12 h-12 rounded-full bg-crowd-highBg text-crowd-high flex items-center justify-center mx-auto">
              <AlertCircle className="w-6 h-6" />
            </div>

            <div className="space-y-1">
              <h1 className="text-lg font-bold text-navy">
                Something went wrong
              </h1>
              <p className="text-xs text-transit-textMuted">
                We encountered an unexpected error while loading this screen. You can try refreshing the page or returning home.
              </p>
            </div>

            <div className="flex items-center justify-center gap-3 pt-2">
              <button
                type="button"
                onClick={this.handleReload}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-[4px] bg-teal text-white hover:bg-tealHover transition-colors min-h-[40px]"
              >
                <RefreshCw className="w-3.5 h-3.5" />
                <span>Reload page</span>
              </button>

              <button
                type="button"
                onClick={this.handleGoHome}
                className="inline-flex items-center gap-1.5 px-3 py-2 text-xs font-semibold rounded-[4px] border border-transit-border bg-transit-bg text-navy hover:bg-white transition-colors min-h-[40px]"
              >
                <Home className="w-3.5 h-3.5" />
                <span>Go to home</span>
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
