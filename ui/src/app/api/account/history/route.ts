import { NextResponse } from "next/server";
import { apiFetch } from "@/lib/api/server";
import { isCleared } from "@/lib/api/types";
import { getUserToken } from "@/lib/auth/user-session";

/** Clear the signed-in user's whole search history. */
export async function DELETE() {
  const token = await getUserToken();
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const result = await apiFetch("/api/v1/account/history", isCleared, { method: "DELETE", token });
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status || 502 });
  return NextResponse.json(result.data);
}
