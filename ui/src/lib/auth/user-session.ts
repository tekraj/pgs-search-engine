import { cache } from "react";
import { cookies } from "next/headers";
import type { NextRequest } from "next/server";
import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api/server";
import { isUserProfile, type UserProfile } from "@/lib/api/types";
import { serverEnv } from "@/lib/env";

/**
 * The public-site user session: the API's signed user token in an httpOnly cookie, kept
 * apart from the admin session (SESSION_COOKIE) so a person can be both. The UI never
 * trusts the cookie's content: GET /api/v1/account/me verifies it on every use.
 */
export const USER_COOKIE = "pgs_user";

export async function getUserToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(USER_COOKIE)?.value || null;
}

/** The signed-in user, or null. Cached per request (React cache). */
export const getUser = cache(async (): Promise<UserProfile | null> => {
  const token = await getUserToken();
  if (!token) return null;
  const result = await apiFetch("/api/v1/account/me", isUserProfile, { token });
  return result.ok ? result.data : null;
});

function cookieIsSecure(request: NextRequest): boolean {
  const mode = serverEnv().cookieSecure;
  if (mode !== "auto") return mode === "always";
  const forwarded = request.headers.get("x-forwarded-proto")?.split(",")[0]?.trim();
  return (forwarded ?? request.nextUrl.protocol.replace(":", "")) === "https";
}

/** A JSON response that also sets the user's session cookie. */
export function withUserSession(
  request: NextRequest,
  body: unknown,
  token: string,
  maxAge: number,
  status = 200,
): NextResponse {
  const response = NextResponse.json(body, { status });
  response.cookies.set(USER_COOKIE, token, {
    httpOnly: true,
    sameSite: "lax",
    secure: cookieIsSecure(request),
    path: "/",
    maxAge,
  });
  return response;
}
