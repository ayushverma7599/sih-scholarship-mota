import RoleLayout from "@/components/RoleLayout";
export default function Layout({ children }: { children: React.ReactNode }) {
  return <RoleLayout roles={["applicant"]}>{children}</RoleLayout>;
}
