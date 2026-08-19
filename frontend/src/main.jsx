import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { AuthProvider, useAuth } from "./auth.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { I18nProvider } from "./i18n";
import "./index.css";

/* The interface language is a property of the signed-in user, so the i18n
   provider has to read auth state — which means living inside AuthProvider.
   This bridge is the smallest way to hand it across. */
function I18nBridge({ children }) {
  const { user } = useAuth();
  return <I18nProvider user={user}>{children}</I18nProvider>;
}

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ErrorBoundary>
      <AuthProvider>
        <I18nBridge>
          <App />
        </I18nBridge>
      </AuthProvider>
    </ErrorBoundary>
  </React.StrictMode>
);
