import { redirect } from "next/navigation";

import { getSessionRole } from "@/lib/backendAuth";

export default async function MembersLayout({ children }: { children: React.ReactNode }) {
	let role: string;
	try {
		role = await getSessionRole();
	} catch {
		redirect("/login?callbackUrl=%2Fmembers");
	}
	if (role !== "admin") {
		redirect("/roles");
	}

	return children;
}