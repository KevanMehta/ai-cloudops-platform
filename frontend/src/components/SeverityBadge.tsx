export default function SeverityBadge({ severity }: { severity: string }) {
  const cls =
    severity === 'high'
      ? 'badge-high'
      : severity === 'medium'
        ? 'badge-medium'
        : 'badge-low';

  return (
    <span className={cls} data-testid={`severity-${severity}`}>
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  );
}
