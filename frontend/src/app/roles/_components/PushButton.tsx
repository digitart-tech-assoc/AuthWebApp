// 役割: ロール変更をDiscordへ送信（Push）

"use client";

import { useState } from "react";
import { pushRolesToDiscord, type PushRolesResponse } from "@/lib/api/roles";
import { btnPrimary } from "./roleStyles";

type Props = {
  onSuccess?: (result: PushRolesResponse) => void;
  onError?: (errors?: string[]) => void;
};

export default function PushButton({ onSuccess, onError }: Props) {
  const [isPending, setIsPending] = useState(false);

  async function handlePush() {
    setIsPending(true);
    try {
      const body = await pushRolesToDiscord();
      if (!body.ok) {
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
      className={btnPrimary}
    >
      {isPending ? <>送信中...</> : <>↑ Discord へ送信</>}
    </button>
  );
}
