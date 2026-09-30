export type User = {
  id: number;
  email: string;
  referral_code: string | null;
};

export type AuthStatus = "loading" | "authenticated" | "anonymous";
