import { NextResponse, type NextRequest } from "next/server";
import { apiFetch, clientIpOf } from "@/lib/api/server";
import { isUserAuthResponse } from "@/lib/api/types";
import { withUserSession } from "@/lib/auth/user-session";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email.trim() : "";
  const password = typeof body?.password === "string" ? body.password : "";
  const displayName = typeof body?.display_name === "string" ? body.display_name.trim() : "";
  if (!email || !password) {
    return NextResponse.json({ error: "Enter your email and a password." }, { status: 400 });
  }
  if (password.length < 12) {
    return NextResponse.json({ error: "The password must be at least 12 characters." }, { status: 400 });
  }

  const result = await apiFetch("/api/v1/account/register", isUserAuthResponse, {
    method: "POST",
    body: { email, password, display_name: displayName || undefined },
    clientIp: clientIpOf(request),
  });
  if (!result.ok) {
    const status = [400, 409, 429, 503].includes(result.status) ? result.status : 502;
    const error =
      status === 409
        ? "An account with this email already exists. Sign in instead."
        : status === 400
          ? "Enter a valid email and a password of at least 12 characters."
          : status === 429
            ? "Too many attempts. Try again in a few minutes."
            : "Sign-up is not available right now; try again later.";
    return NextResponse.json({ error }, { status });
  }
  return withUserSession(request, { user: result.data.user }, result.data.access_token, result.data.expires_in, 201);
}
