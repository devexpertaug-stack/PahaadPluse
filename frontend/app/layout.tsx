import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "PahadPulse — Guest intelligence for the hills",
  description:
    "Hospitality guest-intelligence platform for Mussoorie and Uttarakhand hill towns.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
