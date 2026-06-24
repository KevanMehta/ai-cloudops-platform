import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import StatCard from '../components/StatCard';

describe('StatCard', () => {
  it('renders title and value', () => {
    render(<StatCard title="Monthly Spend" value="$12,345" />);
    expect(screen.getByText('Monthly Spend')).toBeInTheDocument();
    expect(screen.getByTestId('stat-value')).toHaveTextContent('$12,345');
  });

  it('renders subtitle when provided', () => {
    render(
      <StatCard title="Anomalies" value="5" subtitle="Requires investigation" trend="up" />,
    );
    expect(screen.getByText('Requires investigation')).toBeInTheDocument();
  });

  it('has stat-card test id', () => {
    render(<StatCard title="Test" value="100" />);
    expect(screen.getByTestId('stat-card')).toBeInTheDocument();
  });
});

describe('Dashboard stat cards layout', () => {
  it('renders multiple stat cards', () => {
    render(
      <div>
        <StatCard title="Monthly Spend" value="$64,000" subtitle="Current month" />
        <StatCard title="Projected Spend" value="$72,000" subtitle="Forecast" trend="up" />
        <StatCard title="Active Anomalies" value="7" subtitle="Investigate" />
        <StatCard title="Top Service" value="EC2" subtitle="$28,000 / 30d" />
      </div>,
    );
    const cards = screen.getAllByTestId('stat-card');
    expect(cards).toHaveLength(4);
    expect(screen.getByText('EC2')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();
  });
});
