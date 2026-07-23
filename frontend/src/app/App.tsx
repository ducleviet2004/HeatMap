import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { SystemStatusPage } from "../features/system-status/SystemStatusPage";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchInterval: 30_000 } },
});

export function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/status" element={<SystemStatusPage />} />
          <Route path="*" element={<Navigate to="/status" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
