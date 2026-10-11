import { NextResponse } from "next/server";
import { apiFetch, isEmpty } from "@/lib/api/server";
import { USER_COOKIE, getUserToken } from "@/lib/auth/user-session";

export async function POST() {
  // Revoke the token at the API first, so a copied cookie stops working too.
  const token = await getUserToken();
  if (token) await apiFetch("/api/v1/account/logout", isEmpty, { method: "POST", token });
  const response = NextResponse.json({ ok: true });
  response.cookies.delete(USER_COOKIE);
  return response;
}
