"use client";

import TextInput from "./TextInput";

interface NameInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export default function NameInput({
  value,
  onChange,
  error,
  disabled = false,
}: NameInputProps) {
  return (
    <TextInput
      id="name"
      label="名前"
      placeholder="山田太郎"
      value={value}
      onChange={onChange}
      error={error}
      required={true}
      disabled={disabled}
    />
  );
}
