"use client";

import TextInput from "./TextInput";

interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export function normalizePhoneNumber(value: string): string {
  return value.normalize("NFKC").replace(/\D/g, "");
}

export default function PhoneInput({
  value,
  onChange,
  error,
  disabled = false,
}: PhoneInputProps) {
  return (
    <TextInput
      id="phone"
      label="電話番号"
      placeholder="09012345678"
      value={value}
      onChange={(nextValue) => onChange(normalizePhoneNumber(nextValue))}
      error={error}
      required={true}
      type="tel"
      disabled={disabled}
    />
  );
}
