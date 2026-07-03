import { NextResponse } from "next/server";

const protectedRoutes = [
  "/doctors",
  "/doctor",
  "/admin",
  "/appointments",
  "/video-call",
  "/onboarding",
];

export function middleware(request) {
  const token = request.cookies.get("access_token")?.value;

  const { pathname } = request.nextUrl;

  const isProtected = protectedRoutes.some((route) =>
    pathname.startsWith(route)
  );

  if (isProtected && !token) {
    return NextResponse.redirect(new URL("/sign-in", request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    "/doctor/:path*",
    "/doctors/:path*",
    "/admin/:path*",
    "/appointments/:path*",
    "/video-call/:path*",
    "/onboarding/:path*",
  ],
};