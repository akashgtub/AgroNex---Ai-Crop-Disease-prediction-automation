import { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import { GOOGLE_CLIENT_ID, verifyGoogleTokenWithBackend } from './googleAuth';
import './googleAuth.css';

/**
 * AgroNexGoogleLogin - Reusable Google OAuth Sign-In Component
 *
 * Encapsulates the Google Sign-In button, credential capture, backend verification,
 * and error/loading states.
 *
 * @param {Object} props
 * @param {(userData: object) => void} [props.onSuccess] Callback on successful verification
 * @param {(error: Error) => void} [props.onError] Callback on verification failure
 */
export function AgroNexGoogleLogin({ onSuccess, onError }) {
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);

  const isConfigured = Boolean(
    GOOGLE_CLIENT_ID &&
    GOOGLE_CLIENT_ID !== 'YOUR_GOOGLE_CLIENT_ID' &&
    GOOGLE_CLIENT_ID !== 'your_google_client_id_here'
  );

  const handleCredentialSuccess = async (credentialResponse) => {
    try {
      setIsLoading(true);
      setErrorMessage(null);

      if (!credentialResponse?.credential) {
        throw new Error('No credential token received from Google.');
      }

      // Securely verify token with backend
      const response = await verifyGoogleTokenWithBackend(credentialResponse.credential);

      if (onSuccess) {
        onSuccess(response);
      }
    } catch (err) {
      console.error('Google Sign-In failed:', err);
      const displayMessage = err?.message || 'Google authentication failed. Please try again.';
      setErrorMessage(displayMessage);
      if (onError) {
        onError(err);
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleCredentialError = () => {
    const errorMsg = 'Google Sign-In was cancelled or failed to initialize.';
    setErrorMessage(errorMsg);
    if (onError) {
      onError(new Error(errorMsg));
    }
  };

  return (
    <div className="agronex-google-auth-container">
      {isLoading && (
        <div className="agronex-google-loading" role="status" aria-live="polite">
          <span className="inline-block animate-spin mr-1">⌛</span>
          Verifying Google account...
        </div>
      )}

      {errorMessage && (
        <div className="agronex-google-error" role="alert">
          {errorMessage}
        </div>
      )}

      {!isConfigured ? (
        <div className="agronex-google-notice">
          <strong>Google OAuth Notice:</strong>
          <p className="mt-1">
            Google Client ID is not configured. Set <code>VITE_GOOGLE_CLIENT_ID</code> in <code>frontend/.env</code> to enable live Google Sign-In.
          </p>
        </div>
      ) : (
        <div className="agronex-google-btn-wrapper">
          <GoogleLogin
            onSuccess={handleCredentialSuccess}
            onError={handleCredentialError}
            shape="pill"
            theme="outline"
            size="large"
            text="continue_with"
            useOneTap={false}
          />
        </div>
      )}
    </div>
  );
}

export default AgroNexGoogleLogin;
