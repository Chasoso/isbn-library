import { UserManager, WebStorageStateStore } from "oidc-client-ts";
import { config } from "../config";

export const userManager = new UserManager({
  authority: config.cognitoAuthority,
  client_id: config.cognitoClientId,
  redirect_uri: config.redirectUri,
  post_logout_redirect_uri: config.logoutRedirectUri,
  response_type: "code",
  scope: config.scope,
  userStore: new WebStorageStateStore({ store: window.localStorage }),
  automaticSilentRenew: false,
});

export const signIn = async (): Promise<void> => {
  await userManager.signinRedirect();
};

export const handleSignInCallback = async (): Promise<void> => {
  await userManager.signinRedirectCallback();
};

export const signOut = async (): Promise<void> => {
  await userManager.signoutRedirect();
};
