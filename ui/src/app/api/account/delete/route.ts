import { NextResponse, type NextRequest } from "next/server";
import { apiFetch, clientIpOf, isEmpty } from "@/lib/api/server";
import { USER_COOKIE, getUserToken } from "@/lib/auth/user-session";

/** Delete the signed-in user's account and history (needs the password). */
export async function POST(request: NextRequest) {
  const token = await getUserToken();
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const body = await request.json().catch(() => null);
  const password = typeof body?.password === "string" ? body.password : "";
  if (!password) return NextResponse.json({ error: "Enter your password to confirm." }, { status: 400 });
  const result = await apiFetch("/api/v1/account/delete", isEmpty, {
    method: "POST",
    token,
    body: { password },
    clientIp: clientIpOf(request),
  });
  if (!result.ok) {
    const error = result.status === 401 ? "The password is wrong." : result.status === 429 ? "Too many attempts. Try again later." : result.error;
    return NextResponse.json({ error }, { status: result.status || 502 });
  }
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(USER_COOKIE);
  return response;
}
