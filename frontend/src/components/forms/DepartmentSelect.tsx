"use client";

import { ALL_DEPARTMENTS } from "@/lib/validation";

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
  return (
    <div style={{ marginBottom: "16px" }}>
      <label htmlFor="department" style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
        学部学科
        <span style={{ color: "#dc2626" }}>*</span>
      </label>
      <select
        id="department"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        style={{
          width: "100%",
          padding: "8px 12px",
          border: error ? "2px solid #dc2626" : "1px solid #cbd5e1",
          borderRadius: "6px",
          fontSize: "14px",
          boxSizing: "border-box",
          opacity: disabled ? 0.6 : 1,
          cursor: disabled ? "not-allowed" : "pointer",
        }}
      >
        <option value="">選択してください</option>
        {list.map((dept) => (
          <option key={dept} value={dept}>
            {dept}
          </option>
        ))}
      </select>
      {error && (
        <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
          {error}
        </p>
      )}
    </div>
  );
}
