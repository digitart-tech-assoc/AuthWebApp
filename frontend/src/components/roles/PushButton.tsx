// 役割: ロール変更をDiscordへ送信（Push）

"use client";

import { useState } from "react";
import styles from "./roles.module.css";

type PushResult = {
  updated?: number;
  created?: number;
  deleted?: number;
  reordered?: number;
  errors?: string[];
};

type Props = {
  onSuccess?: (result: PushResult) => void;
  onError?: (errors?: string[]) => void;
};

export default function PushButton({ onSuccess, onError }: Props) {
  const [isPending, setIsPending] = useState(false);

  async function handlePush() {
    setIsPending(true);
    try {
      const res = await fetch("/api/roles/push", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const body = (await res.json()) as {
        ok?: boolean;
        updated?: number;
        created?: number;
        deleted?: number;
        reordered?: number;
        errors?: string[];
      };
      if (!res.ok || !body.ok) {
        onError?.(body.errors);
        return;
      }
      onSuccess?.({
        updated: body.updated ?? 0,
        created: body.created ?? 0,
        deleted: body.deleted ?? 0,
        reordered: body.reordered ?? 0,
      });
    } catch {
      onError?.();
    } finally {
      setIsPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handlePush}
      disabled={isPending}
      className={styles.btnPrimary}
    >
      {isPending ? <>送信中...</> : <>↑ Discord へ送信</>}
    </button>
  );
}
