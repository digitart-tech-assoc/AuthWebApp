"use client";

interface GenderSelectProps {
  value: string | null;
  onChange: (value: string | null) => void;
  disabled?: boolean;
}

export default function GenderSelect({
  value,
  onChange,
  disabled = false,
}: GenderSelectProps) {
  return (
    <div style={{ marginBottom: "16px" }}>
      <label style={{ display: "block", marginBottom: "8px", fontWeight: "600" }}>
        性別
      </label>
      <div style={{ display: "flex", gap: "16px" }}>
        {["male", "female", "other"].map((option) => (
          <label
            key={option}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "4px",
              opacity: disabled ? 0.6 : 1,
              cursor: disabled ? "not-allowed" : "pointer",
            }}
          >
            <input
              type="radio"
              name="gender"
              value={option}
              checked={value === option}
              onChange={(e) => onChange(e.target.value)}
              disabled={disabled}
            />
            <span>
              {option === "male" ? "男性" : option === "female" ? "女性" : "その他"}
            </span>
          </label>
        ))}
      </div>
    </div>
  );
}
