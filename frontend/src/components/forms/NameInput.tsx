"use client";

import TextInput from "./TextInput";
import { validateFullName } from "../../lib/validation";
import { useState } from "react";

interface NameInputProps {
  value: string;
  onChange: (value: string) => void;
  onBlur?: React.FocusEventHandler<HTMLInputElement>;
  error?: string;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
  label?: string;
}

export default function NameInput({
  value,
  onChange,
  onBlur,
  error,
  disabled = false,
  className,
  placeholder,
  label,
}: NameInputProps) {
  const [internalError, setInternalError] = useState<string | undefined>(undefined);

  const handleChange = (v: string) => {
    onChange(v);
    if (v.trim().length === 0) {
      setInternalError("名前を入力してください");
    } else if (!validateFullName(v)) {
      setInternalError("姓と名の間に半角スペースを入れてください（ミドルネームも許容）");
    } else {
      setInternalError(undefined);
    }
  };

  return (
    <TextInput
      id="name"
      label={label ?? "氏名"}
      className={className}
      placeholder={placeholder ?? "山田 太郎"}
      value={value}
      onChange={handleChange}
      onBlur={onBlur}
      error={error ?? internalError}
      required={true}
      disabled={disabled}
    />
  );
}
