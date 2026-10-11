import { NextResponse, type NextRequest } from "next/server";
import { apiFetch } from "@/lib/api/server";
import { isUserProfile } from "@/lib/api/types";
import { getUserToken } from "@/lib/auth/user-session";

export async function PATCH(request: NextRequest) {
  const token = await getUserToken();
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const body = await request.json().catch(() => null);
  if (typeof body?.save_history !== "boolean") {
    return NextResponse.json({ error: "save_history must be true or false." }, { status: 400 });
  }
  const result = await apiFetch("/api/v1/account/settings", isUserProfile, {
    method: "PATCH",
    token,
    body: { save_history: body.save_history },
  });
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status || 502 });
  return NextResponse.json({ user: result.data });
}
