import { Inter } from "next/font/google";
import "./globals.css";
import { Toaster } from "sonner";
import Header from "@/components/header";
import { ThemeProvider } from "@/components/theme-provider";
import { AuthProvider } from "@/context/AuthContext";

const inter = Inter({
  subsets: ["latin"],
});

export const metadata = {
  title: "Healthcare Appointment Management",
  description: "AI Powered Healthcare Appointment Management System",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <link rel="icon" href="/logo.png" sizes="any" />
      </head>

      <body className={inter.className}>
       <AuthProvider>
    <ThemeProvider
        attribute="class"
        defaultTheme="light"
        enableSystem
        disableTransitionOnChange
    >
        <Header />

        <main className="min-h-screen">
            {children}
        </main>

    </ThemeProvider>
</AuthProvider>
      </body>
    </html>
  );
}