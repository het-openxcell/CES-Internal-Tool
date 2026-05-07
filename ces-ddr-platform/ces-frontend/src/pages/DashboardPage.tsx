import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">Canadian Energy Services</p>
          <h1>DDR Operations Console</h1>
        </div>
        <Button>Health Ready</Button>
      </div>
      <div className="status-grid">
        <article>
          <span>Platform</span>
          <strong>Local scaffold</strong>
        </article>
        <article>
          <span>Scope</span>
          <strong>Extraction and reporting foundation</strong>
        </article>
        <article>
          <span>Mode</span>
          <strong>Internal operations</strong>
        </article>
      </div>
    </section>
  );
}
