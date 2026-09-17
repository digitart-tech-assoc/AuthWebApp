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
  const [internalValues, setInternalValues] = useState<string[]>(() => Array(length).fill(""));
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  const isControlled = typeof value === "string";
  const values = isControlled
    ? Array.from({ length }, (_, i) => {
        const c = value[i] ?? "";
        return /[0-9]/.test(c) ? c : "";
      })
    : internalValues;

  useEffect(() => {
    if (autoFocus && inputs.current[0]) inputs.current[0].focus();
  }, [autoFocus]);

  const handleChange = (idx: number, v: string) => {
    const ch = v ? v.replace(/[^0-9]/g, "").slice(-1) : "";
    const next = [...values];
    next[idx] = ch;

    if (!isControlled) {
      setInternalValues(next);
    }
    const code = next.join("");
    onChange?.(code);
    if (next.every((slot) => slot !== "")) {
      onComplete?.(code);
    }

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
