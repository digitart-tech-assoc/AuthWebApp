export function validateFullName(name: string): boolean {
  if (!name || typeof name !== "string") return false;
  const v = name.trim();
  // Require at least one half-width space between family and given name. Allow additional name parts.
  // Example valid: "山田 太郎", "Smith John Paul"
  const re = /^\S+ \S+(?: \S+)*$/u;
  return re.test(v);
}

export default validateFullName;
