import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "VYUD LMS — Персональный трек обучения",
  description: "Генерируйте персональные дорожные карты обучения с помощью ИИ",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
