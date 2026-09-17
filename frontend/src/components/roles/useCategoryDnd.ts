"use client";

import { useCallback } from "react";
import {
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import { arrayMove, sortableKeyboardCoordinates } from "@dnd-kit/sortable";
import type { Category } from "@/types/roles";

interface UseCategoryDndProps {
  categories: Category[];
  setCategories: React.Dispatch<React.SetStateAction<Category[]>>;
  onReorder?: () => void;
}

export function useCategoryDnd({ categories, setCategories, onReorder }: UseCategoryDndProps) {
  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  );

  const reorderCategories = useCallback(
    (oldIndex: number, newIndex: number) => {
      setCategories((prev) => {
        const next = arrayMove(prev, oldIndex, newIndex);
        return next.map((c, i) => ({ ...c, display_order: i }));
      });
      onReorder?.();
    },
    [setCategories, onReorder]
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIdx = categories.findIndex((c) => c.id === active.id);
      const newIdx = categories.findIndex((c) => c.id === over.id);
      if (oldIdx !== -1 && newIdx !== -1) {
        reorderCategories(oldIdx, newIdx);
      }
    },
    [categories, reorderCategories]
  );

  return {
    sensors,
    collisionDetection: closestCenter,
    handleDragEnd,
    reorderCategories,
  };
}
