"use client";

import TextInput from "./TextInput";

interface FuriganaInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

export default function FuriganaInput({
  value,
  onChange,
  error,
  disabled = false,
}: FuriganaInputProps) {
  return (
    <TextInput
      id="furigana"
      label="ふりがな"
      placeholder="やまだたろう"
      value={value}
      onChange={onChange}
      error={error}
      required={true}
      disabled={disabled}
    />
  );
}
