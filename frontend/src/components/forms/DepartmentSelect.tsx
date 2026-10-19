"use client";

import { useState } from "react";
import { ALL_DEPARTMENTS } from "@/lib/validation";

// 学部学科名と衝突しない「その他（手入力）」用の値
const OTHER_VALUE = "__other__";

interface DepartmentSelectProps {
  value: string;
  onChange: (value: string) => void;
  options?: string[]; // optional filtered options
  error?: string;
  disabled?: boolean;
}

export default function DepartmentSelect({
  value,
  onChange,
  options,
  error,
  disabled = false,
}: DepartmentSelectProps) {
  const list = options && options.length > 0 ? options : ALL_DEPARTMENTS;
  const [otherSelected, setOtherSelected] = useState(false);
  // 選択肢にない既存の値（手入力された値など）は「その他（手入力）」として復元する
  const isOther = otherSelected || (value !== "" && !list.includes(value));

  const fieldStyle: React.CSSProperties = {
    width: "100%",
    padding: "8px 12px",
    border: error ? "2px solid #dc2626" : "1px solid #cbd5e1",
    borderRadius: "6px",
    fontSize: "14px",
    boxSizing: "border-box",
    opacity: disabled ? 0.6 : 1,
  };

  return (
    <div style={{ marginBottom: "16px" }}>
      <label htmlFor="department" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
        学部学科
        <span style={{ color: "#dc2626" }}>*</span>
      </label>
      <select
        id="department"
        value={isOther ? OTHER_VALUE : value}
        onChange={(e) => {
          if (e.target.value === OTHER_VALUE) {
            setOtherSelected(true);
            onChange("");
          } else {
            setOtherSelected(false);
            onChange(e.target.value);
          }
        }}
        disabled={disabled}
        style={{ ...fieldStyle, cursor: disabled ? "not-allowed" : "pointer" }}
      >
        <option value="">選択してください</option>
        {list.map((dept) => (
          <option key={dept} value={dept}>
            {dept}
          </option>
        ))}
        <option value={OTHER_VALUE}>その他（手入力）</option>
      </select>
      {isOther && (
        <input
          id="department-other"
          type="text"
          aria-label="学部学科（手入力）"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="例: 〇〇学部〇〇学科"
          maxLength={100}
          disabled={disabled}
          style={{ ...fieldStyle, marginTop: "8px" }}
        />
      )}
      {error && (
        <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
          {error}
        </p>
      )}
    </div>
  );
}
