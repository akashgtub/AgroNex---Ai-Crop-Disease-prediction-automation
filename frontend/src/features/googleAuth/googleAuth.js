/**
 * Google OAuth Configuration and API Client
 * Reads Vite environment variable VITE_GOOGLE_CLIENT_ID
 */

export const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

/**
 * Sends the Google ID token credential to the backend verification endpoint.
 *
 * @param {string} credential - The Google ID token (JWT) returned from Google Identity Services
 * @returns {Promise<{success: boolean, user: {google_id: string, email?: string, name?: string, picture?: string}}>}
 */
export async function verifyGoogleTokenWithBackend(credential) {
  if (!credential) {
    throw new Error('Credential is required for Google authentication.');
  }

  const response = await fetch(`${API_BASE_URL}/api/google-auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ credential }),
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const errorDetail = data?.detail || `Authentication failed with status ${response.status}`;
    throw new Error(errorDetail);
  }

  return data;
}
