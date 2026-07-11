"use client";

import { Component, type ReactNode } from "react";
import { AlertTriangle } from "lucide-react";
import { Button } from "./Button";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-[40vh] flex-col items-center justify-center px-6 py-16 text-center">
          <div className="mb-3 flex h-10 w-10 items-center justify-center rounded-lg bg-chrome-100 text-chrome-600">
            <AlertTriangle className="h-5 w-5" aria-hidden />
          </div>
          <h2 className="text-base font-semibold text-chrome-900">
            {this.props.fallbackTitle ?? "Something went wrong"}
          </h2>
          <p className="mt-1 max-w-md text-sm text-chrome-500">
            This page hit an unexpected error. You can retry or return to the alert queue.
          </p>
          <div className="mt-4 flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              onClick={() => this.setState({ error: null })}
            >
              Try again
            </Button>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                window.location.href = "/";
              }}
            >
              Back to queue
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
