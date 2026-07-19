import { Dashboard } from "@/components/Dashboard";
import { getDashboard } from "@/lib/api";

export default async function Home() {
  return <Dashboard data={await getDashboard()} />;
}
