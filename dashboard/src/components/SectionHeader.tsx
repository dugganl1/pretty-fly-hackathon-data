interface SectionHeaderProps {
  title: string;
  subtitle?: string;
}

export default function SectionHeader({ title, subtitle }: SectionHeaderProps) {
  return (
    <div className="mb-6">
      <h2 className="text-xl font-bold text-white tracking-tight">{title}</h2>
      {subtitle && (
        <p className="text-sm text-neutral-500 mt-1">{subtitle}</p>
      )}
    </div>
  );
}
