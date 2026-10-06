import { Activity, Bug, Globe, LayoutDashboard, Server, ShieldAlert, Workflow, type LucideIcon } from "lucide-react";

// The dashboard's sections, in page order. The sidebar and the mobile section
// bar both link to these ids.
export const SECTIONS: { id: string; label: string; icon: LucideIcon }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "pipeline", label: "Pipeline", icon: Workflow },
  { id: "services", label: "Services", icon: Activity },
  { id: "infrastructure", label: "Infrastructure", icon: Server },
  { id: "domains", label: "Websites", icon: Globe },
  { id: "logs", label: "Logs", icon: Bug },
  { id: "security", label: "Security", icon: ShieldAlert },
];
