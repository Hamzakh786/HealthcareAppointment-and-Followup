"use client";

import { useEffect, useState } from "react";
import api from "@/lib/api";
import Link from "next/link";

export default function DoctorSpecialtyPage({ params }) {
  const { specialty } = params;

  const [doctors, setDoctors] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDoctors() {
      try {
        const res = await api.get(
          `/doctors/search?specialization=${specialty}`
        );

        setDoctors(res.data.results || res.data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }

    fetchDoctors();
  }, [specialty]);

  if (loading) {
    return (
      <div className="mt-20 text-center text-lg">
        Loading doctors...
      </div>
    );
  }

  return (
    <div className="container mx-auto mt-24">

      <h1 className="mb-8 text-4xl font-bold capitalize">
        {decodeURIComponent(specialty)}
      </h1>

      {doctors.length === 0 ? (
        <div className="text-center">

          <h2 className="text-2xl font-semibold">
            No doctors available
          </h2>

          <p className="mt-2 text-gray-500">
            No doctors found in this specialty.
          </p>

        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">

          {doctors.map((doctor) => (
            <div
              key={doctor.doctor_id}
              className="rounded-xl border bg-white p-6 shadow"
            >
              <h2 className="text-xl font-bold">
                {doctor.specialization}
              </h2>

              <p className="mt-2">
                <strong>Qualification:</strong>{" "}
                {doctor.qualification}
              </p>

              <p>
                <strong>Experience:</strong>{" "}
                {doctor.experience} Years
              </p>

              <p>
                <strong>Consultation Fee:</strong> ₹
                {doctor.consultation_fee}
              </p>

              <Link
                href={`/appointments/book/${doctor.doctor_id}`}
                className="mt-5 block rounded-lg bg-blue-600 py-2 text-center text-white hover:bg-blue-700"
              >
                Book Appointment
              </Link>
            </div>
          ))}

        </div>
      )}
    </div>
  );
}