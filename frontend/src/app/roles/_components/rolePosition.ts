import type { Category, Role } from "@/types/roles";

export function calcNewRoleInsertionIndex(
  roles: Role[],
  categories: Category[],
  categoryId: string | null,
  botPosition?: number
): number {
  const orderedRoles = [...roles].sort((a, b) => b.position - a.position);
  const orderedCategories = [...categories].sort((a, b) => a.display_order - b.display_order);
  let insertionIndex = orderedRoles.length;
  const categoryIndex = orderedCategories.findIndex((category) => category.id === categoryId);

  if (categoryIndex !== -1) {
    const selectedCategory = orderedCategories[categoryIndex];
    const rolesInCategory = (id: string) => orderedRoles.filter((role) => role.category_id === id);
    const selectedRoles = rolesInCategory(selectedCategory.id);

    if (selectedRoles.length > 0) {
      const bottomRole = selectedRoles[selectedRoles.length - 1];
      insertionIndex = orderedRoles.findIndex((role) => role.role_id === bottomRole.role_id) + 1;
    } else {
      const previousCategory = orderedCategories
        .slice(0, categoryIndex)
        .reverse()
        .find((category) => rolesInCategory(category.id).length > 0);

      if (previousCategory) {
        const previousRoles = rolesInCategory(previousCategory.id);
        const bottomRole = previousRoles[previousRoles.length - 1];
        insertionIndex = orderedRoles.findIndex((role) => role.role_id === bottomRole.role_id) + 1;
      } else {
        const nextCategory = orderedCategories
          .slice(categoryIndex + 1)
          .find((category) => rolesInCategory(category.id).length > 0);

        if (nextCategory) {
          const topRole = rolesInCategory(nextCategory.id)[0];
          insertionIndex = orderedRoles.findIndex((role) => role.role_id === topRole.role_id);
        }
      }
    }
  }

  const firstEditableIndex = botPosition === undefined
    ? 0
    : orderedRoles.findIndex((role) => role.position < botPosition);
  const minimumEditableIndex = firstEditableIndex === -1 ? orderedRoles.length : firstEditableIndex;

  return Math.max(minimumEditableIndex, Math.min(insertionIndex, orderedRoles.length));
}
