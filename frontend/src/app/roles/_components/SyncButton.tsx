// 役割: Discordからロールを取得（Pull）

"use client";

import { useState } from "react";
import { refreshRolesFromDiscord } from "@/lib/api/roles";
import { btnSync } from "./roleStyles";

type Props = {
  onSuccess?: (count: number) => void;
  onError?: () => void;
};

export default function SyncButton({ onSuccess, onError }: Props) {
  const [isPending, setIsPending] = useState(false);

  async function handleSync() {
    setIsPending(true);
    try {
      const body = await refreshRolesFromDiscord();
      if (!body.ok) {
        onError?.();
        return;
      }
      onSuccess?.(body.roles ?? 0);
    } catch {
      onError?.();
    } finally {
      setIsPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={handleSync}
      disabled={isPending}
      className={btnSync}
    >
      {isPending ? (
        <>
          <LoadingDots /> 取得中...
        </>
      ) : (
        <>↓ Discord から取得</>
      )}
    </button>
  );
}

function LoadingDots() {
  return <span className="tracking-widest">●●●</span>;
}
