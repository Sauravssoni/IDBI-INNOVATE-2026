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
        light: {
          bg: "#F1F5F8", // Page background
          card: "#FFFFFF", // Cards
          elevated: "#F7F9FB", // Secondary surface
          text: "#172B4D", // Primary text
          secondary: "#52667A", // Secondary text
          muted: "#7C8C9C", // Muted text
          border: "#D6E0E8" // Border
        },
        brand: {
          teal: "#007C72", // Primary teal
          tealHover: "#00645D", // Teal dark
          softTeal: "#E5F4F1", // Soft teal
          amber: "#B7791F", // Amber
          softAmber: "#FFF4DB", // Approximate soft amber for backgrounds
          red: "#B83232", // Red
          softRed: "#FCEAEA", // Approximate soft red for backgrounds
          nav: "#102A43", // Header/sidebar
          navHover: "#0A1F33",
        }
      },
    },
  },
  plugins: [],
};
export default config;
