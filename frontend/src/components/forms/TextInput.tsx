"use client";

interface TextInputProps {
  id: string;
  label: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  error?: string;
  required?: boolean;
  type?: "text" | "tel" | "email";
  disabled?: boolean;
}

export default function TextInput({
  id,
  label,
  placeholder,
  value,
  onChange,
  error,
  required = false,
  type = "text",
  disabled = false,
}: TextInputProps) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <label htmlFor={id} style={{ display: "block", marginBottom: "4px", fontWeight: "600" }}>
        {label}
        {required && <span style={{ color: "#dc2626" }}>*</span>}
      </label>
      <input
        id={id}
        type={type}
        placeholder={placeholder}
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
      />
      {error && (
        <p style={{ color: "#dc2626", fontSize: "12px", marginTop: "4px" }}>
          {error}
        </p>
      )}
    </div>
  );
}
