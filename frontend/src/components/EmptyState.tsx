export default function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="card flex flex-col items-center py-16 text-center" data-testid="empty-state">
      <div className="mb-4 text-4xl opacity-50">📭</div>
      <h3 className="text-lg font-semibold text-slate-200">{title}</h3>
      <p className="mt-2 max-w-md text-sm text-slate-400">{description}</p>
    </div>
  );
}
