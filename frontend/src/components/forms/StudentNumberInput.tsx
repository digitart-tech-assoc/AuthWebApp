"use client";

import TextInput from "./TextInput";

interface StudentNumberInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
}

export default function StudentNumberInput({
  value,
  onChange,
  error,
  disabled = false,
  className,
  placeholder,
}: StudentNumberInputProps) {
  return (
    <TextInput
      id="student_number"
      label={undefined}
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
