import { useParams } from "react-router";

import PlaceholderPage from "@/pages/PlaceholderPage";

export default function ReportsPage() {
  const { id } = useParams();

  return <PlaceholderPage title="Report Detail" eyebrow="Reports" detail={`Report ${id ?? "selected"}`} />;
}
