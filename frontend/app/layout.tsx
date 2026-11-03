import type { Metadata } from "next";
import { Fraunces, Outfit } from "next/font/google";

import { AuthProvider } from "@/components/auth/AuthProvider";

import "./globals.css";

const display = Fraunces({
  subsets: ["latin"],
  variable: "--font-display",
});

const body = Outfit({
  subsets: ["latin"],
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: "NexusAI",
  description: "Authenticated streaming chatbot — Sprint 1 (Gemini free tier)",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} antialiased`}>
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
