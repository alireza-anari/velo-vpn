import { createContext } from "react";
import type { AuthStatus, User } from "./types";

export type AuthContextValue = {
  status: AuthStatus;
  user: User | null;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};

export const AuthContext = createContext<AuthContextValue | null>(null);
