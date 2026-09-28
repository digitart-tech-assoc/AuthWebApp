// 役割: ロール管理画面で使うトグルスイッチ（checkbox ベース）

"use client";

type Props = {
  checked: boolean;
  disabled?: boolean;
  onChange?: (checked: boolean) => void;
  ariaLabel?: string;
};

export default function ToggleSwitch({ checked, disabled = false, onChange, ariaLabel }: Props) {
  return (
    <label className="relative inline-flex h-6 w-10 shrink-0">
      <input
        type="checkbox"
        className="peer sr-only"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange?.(e.target.checked)}
        aria-label={ariaLabel}
      />
      <span className="absolute inset-0 cursor-pointer rounded-full bg-slate-300 transition-colors after:absolute after:top-1 after:left-1 after:size-4 after:rounded-full after:bg-white after:shadow-sm after:transition-transform peer-checked:bg-blue-600 peer-checked:after:translate-x-4 peer-focus-visible:ring-2 peer-focus-visible:ring-blue-500 peer-focus-visible:ring-offset-2 peer-disabled:cursor-not-allowed peer-disabled:opacity-50" />
    </label>
  );
}
