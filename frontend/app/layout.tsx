import type { Metadata } from "next";
import { Montserrat, Inter } from "next/font/google";
import "./globals.css";

const montserrat = Montserrat({
  subsets: ["latin"],
  variable: "--font-headline",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Prism Data Vault | Editorial Data Vault",
  description:
    "Generate strategic advertising insights by combining editorial expertise, brand research, audience data, and market trends.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`dark ${montserrat.variable} ${inter.variable} antialiased`}
    >
      <body className="bg-surface text-on-surface font-body min-h-screen">
        {children}
      </body>
    </html>
  );
}
