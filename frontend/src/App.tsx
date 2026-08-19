import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "@/components/AppLayout";
import { AuthProvider } from "@/features/auth/AuthContext";
import { RequireAuth } from "@/features/auth/ProtectedRoute";
import { ActivitiesPage } from "@/pages/ActivitiesPage";
import { ActivityDetailPage } from "@/pages/ActivityDetailPage";
import { ForgotPasswordPage } from "@/pages/ForgotPasswordPage";
import { HomePage } from "@/pages/HomePage";
import { LoginPage } from "@/pages/LoginPage";
import { RegisterPage } from "@/pages/RegisterPage";
import { ResetPasswordPage } from "@/pages/ResetPasswordPage";
import { AccountPage } from "@/pages/settings/AccountPage";
import { PlaceholderSettingsPage } from "@/pages/settings/PlaceholderSettingsPage";
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
              <Route
                path="privacy"
                element={
                  <PlaceholderSettingsPage
                    title="Privacy"
                    body="Export, deletion, and cookie controls arrive in a later phase. Account deletion will cascade to your running data."
                  />
                }
              />
              <Route
                path="connected-services"
                element={
                  <PlaceholderSettingsPage
                    title="Connected services"
                    body="Garmin Connect will use official OAuth 2.0 once developer credentials are available. PaceLab will not ask for a Garmin password."
                  />
                }
              />
              <Route
                path="preferences"
                element={
                  <PlaceholderSettingsPage
                    title="Preferences"
                    body="Heart-rate ranges and display units will be configurable here. Nothing is hard-coded to a personal Zone 2."
                  />
                }
              />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
