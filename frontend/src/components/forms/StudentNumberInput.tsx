"use client";

import TextInput from "./TextInput";

interface StudentNumberInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
  label?: string;
}

export default function StudentNumberInput({
  value,
  onChange,
  error,
  disabled = false,
  className,
  placeholder,
  label,
}: StudentNumberInputProps) {
  return (
    <TextInput
      id="student_number"
      label={label ?? "学生番号"}
      className={className}
      placeholder={placeholder ?? "A2312345"}
      value={value}
      onChange={(input) => onChange(input.toUpperCase())}
      error={error}
      required={true}
      disabled={disabled}
    />
  );
}
