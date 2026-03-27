"use client";

import TextInput from "./TextInput";
import { validateFurigana } from "@/lib/validation";
import { useState } from "react";

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
  const [internalError, setInternalError] = useState<string | undefined>(undefined);

  const handleChange = (v: string) => {
    onChange(v);
    if (v.trim().length === 0) {
      setInternalError("フリガナを入力してください");
    } else if (!validateFurigana(v)) {
      setInternalError("フリガナはカタカナで、姓と名の間に半角スペースを入れてください");
    } else {
      setInternalError(undefined);
    }
  };

  return (
    <TextInput
      id="furigana"
      label="フリガナ"
      placeholder="ヤマダ タロウ"
      value={value}
      onChange={handleChange}
      error={error ?? internalError}
      required={true}
      disabled={disabled}
    />
  );
}
