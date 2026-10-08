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

  const commit = (next: string[]) => {
    if (!isControlled) {
      setInternalValues(next);
    }
    const code = next.join("");
    onChange?.(code);
    if (next.every((slot) => slot !== "")) {
      onComplete?.(code);
    }
  };

  const handleChange = (idx: number, v: string) => {
    const ch = v ? v.replace(/[^0-9]/g, "").slice(-1) : "";
    const next = [...values];
    next[idx] = ch;
    commit(next);

    // move focus
    if (ch && idx < length - 1) inputs.current[idx + 1]?.focus();
  };

  // 貼り付けた文字列から数字だけを取り出し、各枠に分配する。
  // 全桁分あれば先頭の枠から、足りなければ貼り付けた枠から順に埋める
  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>, idx: number) => {
    e.preventDefault();
    const digits = e.clipboardData.getData("text").replace(/[^0-9]/g, "").slice(0, length);
    if (!digits) return;

    const start = digits.length >= length ? 0 : idx;
    const next = [...values];
    let last = start;
    for (let i = 0; i < digits.length && start + i < length; i++) {
      next[start + i] = digits[i];
      last = start + i;
    }
    commit(next);

    // 最後に埋めた枠の次へ（最後の枠まで埋まった場合は最後の枠へ）フォーカスを移す
    inputs.current[Math.min(last + 1, length - 1)]?.focus();
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
          onPaste={(e) => handlePaste(e, i)}
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
