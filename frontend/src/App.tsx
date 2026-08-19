import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/AppLayout";
import { AuthProvider } from "@/features/auth/AuthContext";
import { RequireAuth } from "@/features/auth/ProtectedRoute";
import { ActivitiesPage } from "@/pages/ActivitiesPage";
import { ActivityDetailPage } from "@/pages/ActivityDetailPage";
import { EasyRunningPage } from "@/pages/EasyRunningPage";
import { CookiePolicyPage } from "@/pages/CookiePolicyPage";
import { ForgotPasswordPage } from "@/pages/ForgotPasswordPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { PrivacyPolicyPage } from "@/pages/PrivacyPolicyPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ResetPasswordPage } from "@/pages/ResetPasswordPage";
import { TermsOfServicePage } from "@/pages/TermsOfServicePage";
import { TrendsPage } from "@/pages/TrendsPage";
import { AccountPage } from "@/pages/settings/AccountPage";
import { ConnectedServicesPage } from "@/pages/settings/ConnectedServicesPage";
import { PreferencesPage } from "@/pages/settings/PreferencesPage";
import { PrivacyPage } from "@/pages/settings/PrivacyPage";
import { SettingsLayout } from "@/pages/settings/SettingsLayout";
import { VerifyEmailPage } from "@/pages/VerifyEmailPage";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/verify-email" element={<VerifyEmailPage />} />
            <Route path="/privacy" element={<PrivacyPolicyPage />} />
            <Route path="/cookies" element={<CookiePolicyPage />} />
            <Route path="/terms" element={<TermsOfServicePage />} />
            <Route
              path="/easy-running"
              element={
                <RequireAuth>
                  <EasyRunningPage />
                </RequireAuth>
              }
            />
            <Route
              path="/trends"
              element={
                <RequireAuth>
                  <TrendsPage />
                </RequireAuth>
              }
            />
            <Route
              path="/activities"
              element={
                <RequireAuth>
                  <ActivitiesPage />
                </RequireAuth>
              }
            />
            <Route
              path="/activities/:activityId"
              element={
                <RequireAuth>
                  <ActivityDetailPage />
                </RequireAuth>
              }
            />
            <Route
              path="/settings"
              element={
                <RequireAuth>
                  <SettingsLayout />
                </RequireAuth>
              }
            >
              <Route index element={<Navigate to="account" replace />} />
              <Route path="account" element={<AccountPage />} />
              <Route path="privacy" element={<PrivacyPage />} />
              <Route path="connected-services" element={<ConnectedServicesPage />} />
              <Route path="preferences" element={<PreferencesPage />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
