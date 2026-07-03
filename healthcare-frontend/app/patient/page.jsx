"use client";

import { useAuth } from "@/context/AuthContext";
import ProtectedRoute from "@/components/ProtectedRoute";

export default function PatientDashboard() {
  const { user } = useAuth();

  return (
    <ProtectedRoute allowedRoles={["PATIENT"]}>
      <div className="container mx-auto mt-24">

        <h1 className="text-4xl font-bold">
          Patient Dashboard
        </h1>

        <div className="mt-8 grid gap-6 md:grid-cols-2">

          <div className="rounded-lg border p-6 shadow">

            <h2 className="text-xl font-semibold mb-4">
              Profile
            </h2>

            <p>
              <strong>Name:</strong> {user?.full_name}
            </p>

            <p>
              <strong>Email:</strong> {user?.email}
            </p>

            <p>
              <strong>Role:</strong> {user?.role}
            </p>

          </div>

          <div className="rounded-lg border p-6 shadow">

            <h2 className="text-xl font-semibold mb-4">
              Quick Actions
            </h2>

            <div className="space-y-3">

              <a
                href="/doctors"
                className="block rounded bg-blue-600 p-3 text-center text-white"
              >
                Book Appointment
              </a>

              <a
                href="/appointments"
                className="block rounded border p-3 text-center"
              >
                My Appointments
              </a>

            </div>

          </div>

        </div>

      </div>
    </ProtectedRoute>
  );
}