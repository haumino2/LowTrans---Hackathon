import type { Metadata } from "next";
import localFont from "next/font/local";
import { AgentFleetProvider } from "@/context/AgentFleetContext";
import "./globals.css";

const geistSans = localFont({
  src: "./fonts/GeistVF.woff",
  variable: "--font-geist-sans",
  weight: "100 900",
});

export const metadata: Metadata = {
  title: "LowTrans — AML & KYT Agent Platform",
  description: "Agent Platform for AML and KYT for Crypto with RAG-powered triage",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} font-sans antialiased`}>
        <AgentFleetProvider>{children}</AgentFleetProvider>
      </body>
    </html>
  );
}
