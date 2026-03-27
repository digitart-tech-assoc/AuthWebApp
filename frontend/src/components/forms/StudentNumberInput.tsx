"use client";

import TextInput from "./TextInput";

interface StudentNumberInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export default function StudentNumberInput({
  value,
  onChange,
  error,
  disabled = false,
}: StudentNumberInputProps) {
  return (
    <TextInput
      id="student_number"
      label="学生番号"
      placeholder="A2312345"
      value={value}
      onChange={(input) => onChange(input.toUpperCase())}
      error={error}
      required={true}
      disabled={disabled}
    />
  );
}
