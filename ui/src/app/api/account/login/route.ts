import { NextResponse, type NextRequest } from "next/server";
import { apiFetch, clientIpOf } from "@/lib/api/server";
import { isUserAuthResponse } from "@/lib/api/types";
import { withUserSession } from "@/lib/auth/user-session";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const email = typeof body?.email === "string" ? body.email.trim() : "";
  const password = typeof body?.password === "string" ? body.password : "";
  if (!email || !password) {
    return NextResponse.json({ error: "Enter your email and password." }, { status: 400 });
  }

  const result = await apiFetch("/api/v1/account/login", isUserAuthResponse, {
    method: "POST",
    body: { email, password },
    clientIp: clientIpOf(request),
  });
  if (!result.ok) {
    const status = [400, 401, 429, 503].includes(result.status) ? result.status : 502;
    const error =
      status === 401 || status === 400
        ? "Invalid email or password."
        : status === 429
          ? "Too many failed attempts. Try again in a few minutes."
          : "Sign-in failed; try again later.";
    return NextResponse.json({ error }, { status: status === 400 ? 401 : status });
  }
  return withUserSession(request, { user: result.data.user }, result.data.access_token, result.data.expires_in);
}
