"use client";

import React, { useState, useEffect } from "react";
import { Sun, Moon, Laptop } from "lucide-react";
import { useTheme } from "./ThemeProvider";

interface ThemeToggleProps {
  className?: string;
  showDropdown?: boolean;
}

export function ThemeToggle({ className = "", showDropdown = false }: ThemeToggleProps) {
  const { theme, resolvedTheme, setTheme, toggleTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted) {
    return (
      <div
        className={`w-9 h-9 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/50 animate-pulse ${className}`}
      />
    );
  }

  if (showDropdown) {
    return (
      <div className={`relative ${className}`}>
        <button
          onClick={() => setOpen(!open)}
          title={`Theme: ${theme}`}
          className="w-9 h-9 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/80 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 flex items-center justify-center transition-all shadow-sm cursor-pointer"
        >
          {resolvedTheme === "dark" ? (
            <Moon className="w-4 h-4 text-indigo-400" />
          ) : (
            <Sun className="w-4 h-4 text-amber-500" />
          )}
        </button>

        {open && (
          <div className="absolute right-0 mt-2 w-32 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xl p-1.5 z-50 space-y-1 animate-in fade-in zoom-in-95">
            <button
              onClick={() => {
                setTheme("light");
                setOpen(false);
              }}
              className={`w-full px-2.5 py-1.5 rounded-xl text-xs flex items-center gap-2 cursor-pointer transition-colors ${
                theme === "light"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              <Sun className="w-3.5 h-3.5 text-amber-500" />
              <span>Light</span>
            </button>
            <button
              onClick={() => {
                setTheme("dark");
                setOpen(false);
              }}
              className={`w-full px-2.5 py-1.5 rounded-xl text-xs flex items-center gap-2 cursor-pointer transition-colors ${
                theme === "dark"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              <Moon className="w-3.5 h-3.5 text-indigo-400" />
              <span>Dark</span>
            </button>
            <button
              onClick={() => {
                setTheme("system");
                setOpen(false);
              }}
              className={`w-full px-2.5 py-1.5 rounded-xl text-xs flex items-center gap-2 cursor-pointer transition-colors ${
                theme === "system"
                  ? "bg-indigo-600 text-white font-semibold"
                  : "text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800"
              }`}
            >
              <Laptop className="w-3.5 h-3.5 text-slate-400" />
              <span>System</span>
            </button>
          </div>
        )}
      </div>
    );
  }

  return (
    <button
      onClick={toggleTheme}
      title={
        resolvedTheme === "dark"
          ? "Switch to Light Mode"
          : "Switch to Dark Mode"
      }
      aria-label="Toggle Theme"
      className={`group relative w-9 h-9 rounded-xl border border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 hover:bg-slate-100 dark:hover:bg-slate-800/90 text-slate-700 dark:text-slate-300 flex items-center justify-center transition-all shadow-sm hover:shadow-md cursor-pointer overflow-hidden ${className}`}
    >
      <span className="sr-only">Toggle theme</span>
      <Sun className="w-4 h-4 text-amber-500 transition-transform duration-300 rotate-0 scale-100 dark:-rotate-90 dark:scale-0 absolute" />
      <Moon className="w-4 h-4 text-indigo-400 transition-transform duration-300 rotate-90 scale-0 dark:rotate-0 dark:scale-100 absolute" />
    </button>
  );
}
