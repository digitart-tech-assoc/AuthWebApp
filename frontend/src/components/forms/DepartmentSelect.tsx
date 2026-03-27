"use client";

const DEPARTMENTS = [
  "経営学部経営学科",
  "経営学部組織内情報学科",
  "文学部日本文学科",
  "文学部英米文学科",
  "文学部フランス文学科",
  "文学部ドイツ文学科",
  "文学部歴史学科",
  "文学部世界史学科",
  "文学部日本史学科",
  "文学部地理学科",
  "理工学部電気電子工学科",
  "理工学部機械創造工学科",
  "理工学部情報テクノロジー学科",
  "理工学部システムデザイン工学科",
  "理工学部化学・生命科学科",
  "教育学部教育学科",
  "総合文化政策学部総合文化政策学科",
  "社会ネットワーク学部社会ネットワーク学科",
];

interface DepartmentSelectProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export default function DepartmentSelect({
  value,
  onChange,
  error,
  disabled = false,
}: DepartmentSelectProps) {
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
        {DEPARTMENTS.map((dept) => (
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
