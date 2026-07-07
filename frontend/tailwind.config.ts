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
          nav: "#0B1F33",
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
        },
        light: {
          bg: "#F4F6F8",
          card: "#FFFFFF",
          elevated: "#F9FAFB",
          text: "#10243E",
          secondary: "#516174",
          muted: "#758397",
          border: "#D7E0E8"
        },
        brand: {
          teal: "#0E7C66",
          tealHover: "#096A58",
          softTeal: "#E6F3EF",
          amber: "#B98216",
          softAmber: "#FFF4DB",
          red: "#B54848",
          softRed: "#FCEAEA"
        }
      },
    },
  },
  plugins: [],
};
export default config;
