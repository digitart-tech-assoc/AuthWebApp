// 役割: ロール管理画面

import { fetchManifest } from "@/actions/manifest";
import RoleAccordion from "@/components/roles/RoleAccordion";

export default async function RolesPage() {
  const manifest = await fetchManifest();
  return (
    <RoleAccordion categories={manifest.categories} roles={manifest.roles} />
  );
}
