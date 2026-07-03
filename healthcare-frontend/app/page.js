import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col justify-center items-center">

      <h1 className="text-5xl font-bold mb-4">
        Healthcare Appointment Management
      </h1>

      <p className="text-gray-500 mb-10">
        Book appointments with doctors quickly and securely.
      </p>

      <div className="flex gap-4">

        <Link
          href="/sign-in"
          className="bg-blue-600 text-white px-6 py-3 rounded-lg"
        >
          Login
        </Link>

        <Link
          href="/sign-up"
          className="border border-blue-600 px-6 py-3 rounded-lg"
        >
          Register
        </Link>

      </div>

    </main>
  );
}