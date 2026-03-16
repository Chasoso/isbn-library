const required = (value: string | undefined, name: string): string => {
  if (!value) {
    throw new Error(`Missing environment variable: ${name}`);
  }

  return value;
};

export const config = {
  apiBaseUrl: required(import.meta.env.VITE_API_BASE_URL, "VITE_API_BASE_URL").replace(
    /\/+$/,
    "",
  ),
  cognitoAuthority: required(
    import.meta.env.VITE_COGNITO_AUTHORITY,
    "VITE_COGNITO_AUTHORITY",
  ),
  cognitoHostedUiDomain: required(
    import.meta.env.VITE_COGNITO_HOSTED_UI_DOMAIN,
    "VITE_COGNITO_HOSTED_UI_DOMAIN",
  ).replace(/\/+$/, ""),
  cognitoClientId: required(
    import.meta.env.VITE_COGNITO_CLIENT_ID,
    "VITE_COGNITO_CLIENT_ID",
  ),
  redirectUri: required(
    import.meta.env.VITE_COGNITO_REDIRECT_URI,
    "VITE_COGNITO_REDIRECT_URI",
  ),
  logoutRedirectUri: required(
    import.meta.env.VITE_COGNITO_LOGOUT_REDIRECT_URI,
    "VITE_COGNITO_LOGOUT_REDIRECT_URI",
  ),
  scope: required(import.meta.env.VITE_COGNITO_SCOPE, "VITE_COGNITO_SCOPE"),
};
