"use client";

import React, { useRef, useState, useEffect } from "react";

type Props = {
  length?: number;
  onComplete?: (code: string) => void;
  autoFocus?: boolean;
  value?: string;
  onChange?: (code: string) => void;
  disabled?: boolean;
};

export default function OTPInput({ length = 6, onComplete, autoFocus = true, value, onChange, disabled = false }: Props) {
  const [values, setValues] = useState<string[]>(Array(length).fill("") );
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    if (autoFocus && inputs.current[0]) inputs.current[0].focus();
  }, [autoFocus]);

  // Notify parent when fully filled
  useEffect(() => {
    const filled = values.every((v) => v !== "");
    const code = values.join("");
    if (filled) {
      onComplete?.(code);
    }
    onChange?.(code);
  }, [values, onComplete, onChange]);

  // Sync external controlled `value` -> internal values
  useEffect(() => {
    if (typeof value === "string") {
      // Build an array of exact `length`, filling missing slots with empty string
      const arr = Array.from({ length }).map((_, i) => {
        const c = value[i] ?? "";
        return /[0-9]/.test(c) ? c : "";
      });
      setValues(arr);
    }
  }, [value, length]);

  const handleChange = (idx: number, v: string) => {
    if (!v) {
      setValues((s) => {
        const next = [...s];
        next[idx] = "";
        return next;
      });
      return;
    }
    const ch = v.replace(/[^0-9]/g, "").slice(-1);
    setValues((s) => {
      const next = [...s];
      next[idx] = ch;
      return next;
    });
    // move focus
    if (ch && idx < length - 1) inputs.current[idx + 1]?.focus();
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, idx: number) => {
    if (e.key === "Backspace" && !values[idx] && idx > 0) {
      inputs.current[idx - 1]?.focus();
    }
  };

  return (
    <div style={{ display: "flex", gap: 8 }}>
      {Array.from({ length }).map((_, i) => (
        <input
          key={i}
          ref={(el) => { inputs.current[i] = el; }}
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={1}
          value={values[i]}
          onChange={(e) => handleChange(i, e.target.value)}
          onKeyDown={(e) => handleKeyDown(e, i)}
          disabled={disabled}
          style={{
            width: 48,
            height: 56,
            textAlign: "center",
            fontSize: 24,
            borderRadius: 8,
            border: "1px solid #cbd5e1",
            background: disabled ? "#f1f5f9" : "white",
          }}
        />
      ))}
    </div>
  );
}
