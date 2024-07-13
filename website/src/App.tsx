import React, { lazy, Suspense } from 'react';
import { Routes, Route } from 'react-router-dom';
import { Provider } from 'jotai';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import Toast from './components/common/Toast';
import ProtectedRoute from './components/common/ProtectedRoute';

const HomePage = lazy(() => import('./components/pages/HomePage.tsx'));
const LoginPage = lazy(() => import('./components/pages/LoginPage.tsx'));
const SignUpPage = lazy(() => import('./components/pages/SignUpPage.tsx'));
const PasswordResetPage = lazy(() => import('./components/pages/PasswordResetPage.tsx'));
const ProfilePage = lazy(() => import('./components/pages/ProfilePage.tsx'));

const App: React.FC = () => {
  return (
    <Provider>
      <Header />
      <Toast />
      <Suspense fallback={<div>Loading...</div>}>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignUpPage />} />
          <Route path="/reset-password" element={<PasswordResetPage />} />
          <Route
            path="/profile"
            element={
              // <ProtectedRoute>
                <ProfilePage />
              // </ProtectedRoute>
            }
          />
        </Routes>
      </Suspense>
      <Footer />
    </Provider>
  );
};

export default App;