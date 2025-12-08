// proxy.ts
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

const protectedRoutes = [
  "/dashboard",
  "/billing",
  "/projects",
  "/history",
  "/settings",
  "/profile",
  "/team",
  "/voices",
  "/subtitles",
  "/video",
  "/audio",
];
const publicRoutes = ["/", "/login", "/signup", "/forgot-password"];
const authRoutes = ["/login", "/signup"];

function getCookieValue(
  cookieOrMaybeObj: string | { value: string } | undefined
) {
  if (!cookieOrMaybeObj) return undefined;
  if (typeof cookieOrMaybeObj === "string") return cookieOrMaybeObj;
  return cookieOrMaybeObj?.value;
}

function normalizePathname(pathname: string) {
  if (pathname === "/") return pathname;
  return pathname.replace(/\/+$/, "");
}

export default async function proxy(request: NextRequest) {
  const rawPath = request.nextUrl.pathname;
  const pathname = normalizePathname(rawPath);

  const rawSession = request.cookies.get("octavia_session");
  const sessionValue = getCookieValue(rawSession);

  const isProtectedRoute = protectedRoutes.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  );
  const isAuthRoute = authRoutes.includes(pathname);

  // Protect routes - redirect to login if no session
  if (isProtectedRoute && !sessionValue) {
    return NextResponse.redirect(new URL("/login", request.url));
  }

  // Redirect logged-in users away from auth pages
  if (isAuthRoute && sessionValue) {
    try {
      const response = await fetch(
        `${process.env.BACKEND_URL}/api/v1/auth/me`,
        {
          headers: {
            Cookie: `octavia_session=${sessionValue}`,
          },
          cache: "no-store",
        }
      );

      if (response.ok) {
        return NextResponse.redirect(new URL("/dashboard", request.url));
      }
    } catch (error) {
      console.error("Session verification failed:", error);
    }
  }

  // Redirect logged-in users away from home page
  if (pathname === "/" && sessionValue) {
    try {
      const response = await fetch(
        `${process.env.BACKEND_URL}/api/v1/auth/me`,
        {
          headers: {
            Cookie: `octavia_session=${sessionValue}`,
          },
          cache: "no-store",
        }
      );

      if (response.ok) {
        return NextResponse.redirect(new URL("/dashboard", request.url));
      }
    } catch (error) {
      console.error("Session verification failed:", error);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/((?!api|_next/static|_next/image|favicon.ico).*)"],
};
