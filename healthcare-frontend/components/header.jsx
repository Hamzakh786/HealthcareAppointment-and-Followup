"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import {
  Calendar,
  ShieldCheck,
  Stethoscope,
  LogOut,
  User,
} from "lucide-react";
import api from "@/lib/api";

export default function Header() {
  const router = useRouter();

  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");

    if (!token) return;

    api
      .get("/auth/me")
      .then((res) => setUser(res.data))
      .catch(() => {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      });
  }, []);

  const logout = () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    router.push("/sign-in");
  };

  return (
    <header className="fixed top-0 z-50 w-full border-b bg-white shadow-sm">
      <nav className="container mx-auto flex h-16 items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2">
          <Image
            src="/logo-single.png"
            alt="Healthcare"
            width={180}
            height={50}
            className="h-10 w-auto"
          />
        </Link>

        <div className="flex items-center gap-3">
          {user ? (
            <>
              {user.role === "ADMIN" && (
                <Link href="/admin">
                  <Button variant="outline">
                    <ShieldCheck className="mr-2 h-4 w-4" />
                    Admin
                  </Button>
                </Link>
              )}

              {user.role === "DOCTOR" && (
                <Link href="/doctor">
                  <Button variant="outline">
                    <Stethoscope className="mr-2 h-4 w-4" />
                    Doctor
                  </Button>
                </Link>
              )}

              {user.role === "PATIENT" && (
                <Link href="/appointments">
                  <Button variant="outline">
                    <Calendar className="mr-2 h-4 w-4" />
                    Appointments
                  </Button>
                </Link>
              )}

              <div className="hidden md:flex items-center gap-2 rounded-lg border px-3 py-2">
                <User className="h-4 w-4" />
                <span>{user.full_name}</span>
              </div>

              <Button variant="destructive" onClick={logout}>
                <LogOut className="mr-2 h-4 w-4" />
                Logout
              </Button>
            </>
          ) : (
            <>
              <Link href="/sign-in">
                <Button>Login</Button>
              </Link>

              <Link href="/sign-up">
                <Button variant="outline">Register</Button>
              </Link>
            </>
          )}
        </div>
      </nav>
    </header>
  );
}