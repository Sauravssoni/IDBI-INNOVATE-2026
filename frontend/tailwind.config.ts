import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        navy: {
          900: "#08111C",
          800: "#0C1623",
          700: "#111E2D",
          600: "#152537",
          500: "#26384B",
        },
        pulse: {
          600: "#1D927C",
          500: "#16836F",
          400: "#143A35",
        },
        bank: {
          warning: "#C7922C",
          danger: "#B85C5C",
          info: "#527A9D",
          border: "#26384B",
          muted: "#7F8D9D",
          secondary: "#AAB6C4",
          main: "#F4F7FA",
        }
      },
    },
  },
  plugins: [],
};
export default config;
