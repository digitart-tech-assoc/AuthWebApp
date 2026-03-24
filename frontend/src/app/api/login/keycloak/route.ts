import { signIn } from "@/auth";

export async function POST(request: Request) {
	const formData = await request.formData();
	const callbackValue = formData.get("callbackUrl");
	const callbackUrl = typeof callbackValue === "string" && callbackValue.startsWith("/") ? callbackValue : "/roles";

	return signIn("keycloak", { redirectTo: callbackUrl });
}