import type { Metadata } from "next";
import { Inter, Poppins } from "next/font/google";
import "./globals.css";

/** Clean, highly readable body sans. */
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-sans",
});

/** Expressive display face for headings and the brand mark. */
const poppins = Poppins({
  subsets: ["latin"],
  display: "swap",
  weight: ["500", "600", "700"],
  variable: "--font-display",
});

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
    <html lang="en" className={`${inter.variable} ${poppins.variable}`}>
      <body>{children}</body>
    </html>
  );
}
