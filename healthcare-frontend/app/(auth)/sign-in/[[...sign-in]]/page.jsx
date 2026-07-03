"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function SignInPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [form, setForm] = useState({
    email: "",
    password: "",
  });

  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);

    try {
      // Login request
      const response = await api.post("/auth/login", form);

      const tokens = response.data;

      // Get logged-in user details
      const me = await api.get("/auth/me", {
        headers: {
          Authorization: `Bearer ${tokens.access_token}`,
        },
      });

      // Save tokens and user in AuthContext
      login(
        tokens.access_token,
        tokens.refresh_token,
        me.data
      );

      // Redirect based on role
      switch (me.data.role) {
        case "ADMIN":
          router.push("/admin");
          break;

        case "DOCTOR":
          router.push("/doctor");
          break;

        case "PATIENT":
          router.push("/doctors");
          break;

        default:
          router.push("/");
      }
    } catch (err) {
      console.error(err);

      alert(
        err.response?.data?.detail ||
          "Invalid email or password."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-blue-50">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md rounded-xl bg-white p-8 shadow-lg"
      >
        <h1 className="mb-6 text-center text-3xl font-bold text-blue-700">
          Login
        </h1>

        <input
          type="email"
          placeholder="Email"
          className="mb-4 w-full rounded border p-3"
          value={form.email}
          onChange={(e) =>
            setForm({
              ...form,
              email: e.target.value,
            })
          }
          required
        />

        <input
          type="password"
          placeholder="Password"
          className="mb-6 w-full rounded border p-3"
          value={form.password}
          onChange={(e) =>
            setForm({
              ...form,
              password: e.target.value,
            })
          }
          required
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-blue-600 p-3 text-white transition hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Signing in..." : "Sign In"}
        </button>

        <p className="mt-5 text-center text-sm">
          Don't have an account?{" "}
          <a
            href="/sign-up"
            className="font-semibold text-blue-600 hover:underline"
          >
            Register
          </a>
        </p>
      </form>
    </div>
  );
}