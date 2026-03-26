"use client";

import React, { useRef, useState, useEffect } from "react";

type Props = {
  length?: number;
  onComplete?: (code: string) => void;
  autoFocus?: boolean;
};

export default function OTPInput({ length = 6, onComplete, autoFocus = true }: Props) {
  const [values, setValues] = useState<string[]>(Array(length).fill(""));
  const inputs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    if (autoFocus && inputs.current[0]) inputs.current[0].focus();
  }, [autoFocus]);

  useEffect(() => {
    const filled = values.every((v) => v !== "");
    if (filled) {
      onComplete?.(values.join(""));
    }
  }, [values, onComplete]);

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
          style={{
            width: 48,
            height: 56,
            textAlign: "center",
            fontSize: 24,
            borderRadius: 8,
            border: "1px solid #cbd5e1",
          }}
        />
      ))}
    </div>
  );
}
