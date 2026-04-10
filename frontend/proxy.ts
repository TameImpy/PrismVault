import { NextRequest, NextResponse } from "next/server";

const COOKIE_NAME = "access_token";

export function proxy(request: NextRequest) {
  const token = request.cookies.get(COOKIE_NAME);

  if (!token) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("redirect", request.nextUrl.pathname);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/app/:path*", "/assistant/:path*"],
};
