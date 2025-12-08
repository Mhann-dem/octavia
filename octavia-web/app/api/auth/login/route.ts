import { NextResponse } from "next/server";
import { z } from "zod";

const loginSchema = z.object({
  email: z.email({ message: "Invalid email address" }),
  password: z.string().min(1, { message: "Password is required" }),
});

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const validatedData = loginSchema.parse(body);

    const backendBase = process.env.BACKEND_URL || 'http://localhost:8001';

    const backendResponse = await fetch(
      `${backendBase.replace(/\/$/, '')}/login`,
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          email: validatedData.email,
          password: validatedData.password,
        }),
      }
    );

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json();

      if (errorData.message?.includes("Invalid credentials")) {
        return NextResponse.json(
          { error: "Invalid email or password" },
          { status: 401 }
        );
      }

      return NextResponse.json(
        { error: errorData.message || "Failed to sign in" },
        { status: backendResponse.status }
      );
    }

    const userData = await backendResponse.json();
    const response = NextResponse.json({
      success: true,
      user: userData,
      redirect: "/dashboard",
    });

    if (userData.session_id) {
      response.cookies.set("octavia_session", userData.session_id, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        sameSite: "strict",
        maxAge: 86400,
        path: "/",
      });
    }

    return response;
  } catch (error) {
    if (error instanceof z.ZodError) {
      return NextResponse.json(
        {
          error: "Validation failed",
          errors: error.issues.map((e) => ({
            field: e.path.join("."),
            message: e.message,
          })),
        },
        { status: 400 }
      );
    }

    console.error("Login error:", error);
    return NextResponse.json(
      { error: "An unexpected error occurred" },
      { status: 500 }
    );
  }
}
