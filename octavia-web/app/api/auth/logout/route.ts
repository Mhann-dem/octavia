import { NextResponse } from "next/server";
import { cookies } from "next/headers";

export async function POST() {
  try {
    const cookieStore = cookies();
    const sessionCookie =
      (await cookieStore).get("octavia_session")?.value || "";

    try {
      await fetch(`${process.env.BACKEND_URL}/api/v1/auth/logout`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
          Cookie: `octavia_session=${sessionCookie}`,
        },
      });
    } catch (err) {
      console.error("Backend logout failed (continuing):", err);
    }

    const res = NextResponse.json({
      success: true,
      redirect: "/",
    });
    res.cookies.set("octavia_session", "", { path: "/", maxAge: 0 });

    return res;
  } catch (error) {
    console.error("Logout error:", error);
    return NextResponse.json({ error: "Failed to logout" }, { status: 500 });
  }
}
