import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";
import { config } from "../config";

type MinimalUserManager = {
  getUser: () => Promise<User | null>;
  signinRedirect: () => Promise<void>;
  signinRedirectCallback: () => Promise<unknown>;
  removeUser: () => Promise<void>;
};

const demoUser = {
  expired: false,
  access_token: "demo-access-token",
  profile: {
    email: "demo@example.com",
    name: "Chassso",
  },
} as User;

const mockUserManager: MinimalUserManager = {
  async getUser() {
    return demoUser;
  },
  async signinRedirect() {
    return;
  },
  async signinRedirectCallback() {
    return;
  },
  async removeUser() {
    return;
  },
};

export const userManager: MinimalUserManager = config.e2eDemoMode
  ? mockUserManager
  : new UserManager({
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
  if (config.e2eDemoMode) {
    return;
  }

  await userManager.signinRedirect();
};

export const handleSignInCallback = async (): Promise<void> => {
  if (config.e2eDemoMode) {
    return;
  }

  await userManager.signinRedirectCallback();
};

export const signOut = async (): Promise<void> => {
  await userManager.removeUser();

  if (config.e2eDemoMode) {
    window.location.assign("/");
    return;
  }

  const logoutUrl = new URL(`${config.cognitoHostedUiDomain}/logout`);
  logoutUrl.searchParams.set("client_id", config.cognitoClientId);
  logoutUrl.searchParams.set("logout_uri", config.logoutRedirectUri);

  window.location.assign(logoutUrl.toString());
};
