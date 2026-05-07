type PlaceholderPageProps = {
  title: string;
  eyebrow: string;
  detail: string;
};

export default function PlaceholderPage({ title, eyebrow, detail }: PlaceholderPageProps) {
  return (
    <section className="workspace">
      <div className="workspace-header">
        <div>
          <p className="eyebrow">{eyebrow}</p>
          <h1>{title}</h1>
        </div>
      </div>
      <div className="placeholder-band">
        <span>Workspace</span>
        <strong>{detail}</strong>
      </div>
    </section>
  );
}
