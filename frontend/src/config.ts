const optional = (value: string | undefined, fallback = ""): string => value ?? fallback;

const required = (value: string | undefined, name: string): string => {
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }

  return value;
};

const e2eDemoMode = import.meta.env.VITE_E2E_DEMO_MODE === "true";

export const config = {
  e2eDemoMode,
  apiBaseUrl: (
    e2eDemoMode
      ? optional(import.meta.env.VITE_API_BASE_URL, "http://127.0.0.1:4173")
      : required(import.meta.env.VITE_API_BASE_URL, "VITE_API_BASE_URL")
  ).replace(/\/+$/, ""),
  cognitoAuthority: e2eDemoMode
    ? optional(import.meta.env.VITE_COGNITO_AUTHORITY, "https://example.com/mock-authority")
    : required(import.meta.env.VITE_COGNITO_AUTHORITY, "VITE_COGNITO_AUTHORITY"),
  cognitoHostedUiDomain: (
    e2eDemoMode
      ? optional(import.meta.env.VITE_COGNITO_HOSTED_UI_DOMAIN, "https://example.com/mock-hosted-ui")
      : required(import.meta.env.VITE_COGNITO_HOSTED_UI_DOMAIN, "VITE_COGNITO_HOSTED_UI_DOMAIN")
  ).replace(/\/+$/, ""),
  cognitoClientId: e2eDemoMode
    ? optional(import.meta.env.VITE_COGNITO_CLIENT_ID, "mock-client-id")
    : required(import.meta.env.VITE_COGNITO_CLIENT_ID, "VITE_COGNITO_CLIENT_ID"),
  redirectUri: e2eDemoMode
    ? optional(import.meta.env.VITE_COGNITO_REDIRECT_URI, "http://127.0.0.1:4173/auth/callback")
    : required(import.meta.env.VITE_COGNITO_REDIRECT_URI, "VITE_COGNITO_REDIRECT_URI"),
  logoutRedirectUri: e2eDemoMode
    ? optional(import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI, "http://127.0.0.1:4173")
    : required(
        import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI,
        "VITE_COGNITO_LOGOUT_REDIRECT_URI",
      ),
  scope: e2eDemoMode
    ? optional(import.meta.env.VITE_COGNITO_SCOPE, "openid email profile")
    : required(import.meta.env.VITE_COGNITO_SCOPE, "VITE_COGNITO_SCOPE"),
};
