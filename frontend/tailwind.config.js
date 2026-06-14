/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        ember: "#e8440a", "ember-hover": "#ff5a1f",
        dark: { 900: "#0a0a0a", 800: "#141414", 700: "#1e1e1e", 600: "#2a2a2a" },
      },
      fontFamily: { mono: ["JetBrains Mono", "Fira Code", "monospace"], sans: ["Inter", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};
