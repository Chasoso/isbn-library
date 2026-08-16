import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "ISBN Library Responsive Prototype",
  description: "小さな端末でも次の一冊をすぐ見つけられる、レスポンシブな蔵書管理プロトタイプ。",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja">
      <body>{children}</body>
    </html>
  );
}
