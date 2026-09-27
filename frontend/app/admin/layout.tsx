import RoleLayout from "@/components/RoleLayout";
export default function Layout({ children }: { children: React.ReactNode }) {
  return <RoleLayout roles={["admin"]}>{children}</RoleLayout>;
}
