import { NextResponse } from "next/server";
import { apiFetch, isEmpty } from "@/lib/api/server";
import { SESSION_COOKIE, getSessionToken } from "@/lib/auth/session";

export async function POST() {
  // Revoke the token at the API first, so a copied cookie stops working too.
  const token = await getSessionToken();
  if (token) await apiFetch("/api/v1/auth/logout", isEmpty, { method: "POST", token });
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(SESSION_COOKIE);
  return response;
}
