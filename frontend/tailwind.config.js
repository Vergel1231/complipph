/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        display: ['"Cabinet Grotesk"', "ui-sans-serif", "system-ui"],
        body: ['"Manrope"', "ui-sans-serif", "system-ui"],
      },
      colors: {
        // Earthy palette
        sand: {
          50:  "#FBFAF7",
          100: "#F9F8F6",
          200: "#F0EFEA",
          300: "#E2E0D8",
          400: "#C9C5B7",
          500: "#A8A492",
          600: "#8A9A91",
          700: "#516359",
          800: "#3A4640",
          900: "#1A2E24",
        },
        olive: {
          50:  "#EFF3EF",
          100: "#D8E1D9",
          200: "#A9BBAD",
          300: "#7B9683",
          400: "#52735C",
          500: "#3A6048",
          600: "#2C4C3B",
          700: "#1E3629",
          800: "#152619",
          900: "#0E1A11",
        },
        sage: {
          50:  "#F2F6F2",
          100: "#E1ECE3",
          200: "#C7D9CB",
          300: "#A6BFAD",
          400: "#8FA998",
          500: "#6F8F7A",
        },
        terracotta: {
          50:  "#FDF1ED",
          100: "#F9D9CD",
          200: "#F0AC95",
          300: "#E68669",
          400: "#E06D53",
          500: "#D75A3D",
          600: "#C95B42",
          700: "#A8472F",
          800: "#82351F",
          900: "#5C2415",
        },
        // shadcn semantic tokens
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": { from: { height: 0 }, to: { height: "var(--radix-accordion-content-height)" } },
        "accordion-up": { from: { height: "var(--radix-accordion-content-height)" }, to: { height: 0 } },
        "fade-up": { "0%": { opacity: 0, transform: "translateY(12px)" }, "100%": { opacity: 1, transform: "translateY(0)" } },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-up": "fade-up 0.6s ease-out forwards",
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
};
