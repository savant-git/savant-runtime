import React from "react";
import ReactDOM from "react-dom/client";

import {
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";

import {
  ErrorBoundary,
  type FallbackProps,
} from "react-error-boundary";

import {
  RefreshCcw,
  ShieldAlert,
} from "lucide-react";

import {
  Splyce,
} from "./Splyce";

import "./savant-ui.css";
import "./splyce.css";


const queryClient =
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: 2,
        staleTime: 5000,
        gcTime: 300000,
        refetchOnReconnect: true,
        refetchOnWindowFocus: true,
      },
    },
  });


function Failure({
  error,
  resetErrorBoundary,
}: FallbackProps) {
  return (
    <main
      className="sp-failure"
      role="alert"
    >
      <ShieldAlert
        size={34}
      />

      <strong>
        Splyce runtime isolated a failure.
      </strong>

      <p>
        {
          error instanceof Error
            ? error.message
            : String(error)
        }
      </p>

      <button
        type="button"
        onClick={() => {
          queryClient.clear();
          resetErrorBoundary();
        }}
      >
        <RefreshCcw
          size={14}
        />

        recover
      </button>
    </main>
  );
}


const root =
  document.getElementById(
    "root",
  );

if (!root) {
  throw new Error(
    "Splyce root element is missing",
  );
}


ReactDOM.createRoot(
  root,
).render(
  <React.StrictMode>
    <ErrorBoundary
      FallbackComponent={Failure}
      onReset={() => {
        queryClient.clear();
      }}
    >
      <QueryClientProvider
        client={queryClient}
      >
        <Splyce />
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
);
