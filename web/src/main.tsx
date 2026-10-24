import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ErrorBoundary } from "react-error-boundary";
import App from "./App";
import "./styles.css";

const queryClient = new QueryClient();
createRoot(document.getElementById("root")!).render(
  <StrictMode><ErrorBoundary fallbackRender={({ error }) => <main className="fatal">The client could not start: {error.message}</main>}><QueryClientProvider client={queryClient}><App /></QueryClientProvider></ErrorBoundary></StrictMode>,
);
