import { NextResponse, type NextRequest } from "next/server";
import { apiFetch, isEmpty } from "@/lib/api/server";
import { getUserToken } from "@/lib/auth/user-session";

/** Remove one search from the signed-in user's history. */
export async function DELETE(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const token = await getUserToken();
  if (!token) return NextResponse.json({ error: "Sign in first." }, { status: 401 });
  const { id } = await params;
  if (!/^\d{1,18}$/.test(id)) return NextResponse.json({ error: "Invalid id." }, { status: 400 });
  const result = await apiFetch(`/api/v1/account/history/${id}`, isEmpty, { method: "DELETE", token });
  if (!result.ok) return NextResponse.json({ error: result.error }, { status: result.status || 502 });
  return NextResponse.json({ ok: true });
}
