import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, LineChart, Line, Legend, Cell, PieChart, Pie,
} from 'recharts';
import { useData } from '../data/DataContext';
import SectionHeader from '../components/SectionHeader';
import MetricCard from '../components/MetricCard';
import { formatGBP, formatPct, ym, monthLabel, sum, groupBy } from '../data/utils';

const ACCENT = '#d946ef';
const ACCENT2 = '#8b5cf6';
const MUTED = '#525252';
const POSITIVE = '#22c55e';
const NEGATIVE = '#ef4444';

export default function CustomersSupport() {
  const data = useData();

  // Cohort retention grid
  const cohorts = useMemo(() => {
    const custFirstMonth = new Map<string, string>();
    for (const c of data.customers) {
      custFirstMonth.set(c.customer_id, ym(c.acquisition_date || c.created_at));
    }

    const ordersByCustomer = groupBy(data.orders, (o) => o.customer_id);

    // Group customers by acquisition month
    const cohortMonths = groupBy(data.customers, (c) => ym(c.acquisition_date || c.created_at));
    const sortedCohortMonths = Object.keys(cohortMonths).sort();

    // For each cohort, compute % active at month 0, 1, 2, 3, 4, 5
    return sortedCohortMonths.slice(-12).map((cohortMonth) => {
      const custs = cohortMonths[cohortMonth];
      const row: Record<string, number | string> = { cohort: monthLabel(cohortMonth), size: custs.length };

      for (let offset = 0; offset <= 5; offset++) {
        const [cy, cm] = cohortMonth.split('-').map(Number);
        const targetDate = new Date(cy, cm - 1 + offset, 1);
        const targetYM = `${targetDate.getFullYear()}-${String(targetDate.getMonth() + 1).padStart(2, '0')}`;

        const active = custs.filter((c) => {
          const orders = ordersByCustomer[c.customer_id] || [];
          return orders.some((o) => ym(o.created_at) === targetYM);
        });

        row[`m${offset}`] = custs.length > 0 ? (active.length / custs.length) * 100 : 0;
      }
      return row;
    });
  }, [data]);

  // LTV by acquisition source
  const ltvBySource = useMemo(() => {
    const bySource = groupBy(data.customers, (c) => {
      const src = (c.acquisition_source || '').split('/')[0];
      return src || 'direct';
    });

    return Object.entries(bySource)
      .map(([source, custs]) => ({
        source,
        count: custs.length,
        avgSpent: custs.length > 0 ? sum(custs.map((c) => c.total_spent)) / custs.length : 0,
        avgOrders: custs.length > 0 ? sum(custs.map((c) => c.orders_count)) / custs.length : 0,
      }))
      .sort((a, b) => b.avgSpent - a.avgSpent);
  }, [data]);

  // LTV by gender
  const ltvByGender = useMemo(() => {
    const byGender = groupBy(data.customers, (c) => c.gender_segment_affinity || 'unknown');
    return Object.entries(byGender)
      .filter(([g]) => g !== 'unknown')
      .map(([gender, custs]) => ({
        gender,
        count: custs.length,
        avgSpent: custs.length > 0 ? sum(custs.map((c) => c.total_spent)) / custs.length : 0,
        avgOrders: custs.length > 0 ? sum(custs.map((c) => c.orders_count)) / custs.length : 0,
        repeatRate: custs.length > 0 ? (custs.filter((c) => c.orders_count >= 2).length / custs.length) * 100 : 0,
      }));
  }, [data]);

  // Support volume over time
  const supportVolume = useMemo(() => {
    const byMonth = groupBy(data.supportTickets, (t) => ym(t.created_at));
    return Object.entries(byMonth)
      .map(([month, tickets]) => ({
        month,
        label: monthLabel(month),
        total: tickets.length,
        botResolved: tickets.filter((t) => t.resolved_by === 'bot').length,
        humanResolved: tickets.filter((t) => t.resolved_by === 'human').length,
      }))
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [data]);

  // Support category breakdown
  const supportCategories = useMemo(() => {
    const cats = groupBy(data.supportTickets, (t) => t.category);
    return Object.entries(cats)
      .map(([cat, tickets]) => ({ category: cat, count: tickets.length }))
      .sort((a, b) => b.count - a.count);
  }, [data]);

  // Bot resolution rate trend
  const botResolutionTrend = useMemo(() => {
    const byMonth = groupBy(data.supportTickets, (t) => ym(t.created_at));
    return Object.entries(byMonth)
      .map(([month, tickets]) => {
        const resolved = tickets.filter((t) => t.resolved_by);
        const botResolved = resolved.filter((t) => t.resolved_by === 'bot').length;
        return {
          month,
          label: monthLabel(month),
          rate: resolved.length > 0 ? (botResolved / resolved.length) * 100 : 0,
        };
      })
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [data]);

  // Key metrics
  const metrics = useMemo(() => {
    const totalCustomers = data.customers.length;
    const repeatCustomers = data.customers.filter((c) => c.orders_count >= 2).length;
    const avgLTV = sum(data.customers.map((c) => c.total_spent)) / totalCustomers;
    const avgOrders = sum(data.customers.map((c) => c.orders_count)) / totalCustomers;
    const botRate = data.supportTickets.length > 0
      ? (data.supportTickets.filter((t) => t.resolved_by === 'bot').length / data.supportTickets.length) * 100
      : 0;
    return { totalCustomers, repeatCustomers, repeatRate: (repeatCustomers / totalCustomers) * 100, avgLTV, avgOrders, botRate, totalTickets: data.supportTickets.length };
  }, [data]);

  const catColors = ['#d946ef', '#8b5cf6', '#06b6d4', '#22c55e', '#f59e0b', '#ef4444', '#525252'];

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Customers & Support</h2>
        <p className="text-sm text-neutral-500 mt-1">How customers behave, what they complain about.</p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Total Customers" value={metrics.totalCustomers.toLocaleString()} subtitle={`${formatPct(metrics.repeatRate)} repeat`} />
        <MetricCard label="Avg LTV" value={formatGBP(metrics.avgLTV)} subtitle={`${metrics.avgOrders.toFixed(1)} orders avg`} />
        <MetricCard label="Support Tickets" value={metrics.totalTickets.toLocaleString()} subtitle="Over 24 months" />
        <MetricCard label="Bot Resolution" value={formatPct(metrics.botRate)} subtitle="Room for Fin AI" />
      </div>

      {/* Cohort Retention Grid */}
      <div>
        <SectionHeader title="Cohort Retention" subtitle="% of cohort active in each subsequent month" />
        <div className="bg-surface border border-border rounded-lg overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Cohort</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">Size</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">M0</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">M1</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">M2</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">M3</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">M4</th>
                <th className="text-right py-3 px-3 text-neutral-500 font-medium">M5</th>
              </tr>
            </thead>
            <tbody>
              {cohorts.map((row, i) => (
                <tr key={i} className="border-b border-border/50">
                  <td className="py-2 px-4 text-white font-medium">{row.cohort}</td>
                  <td className="py-2 px-3 text-right font-mono text-neutral-400">{(row.size as number).toLocaleString()}</td>
                  {[0, 1, 2, 3, 4, 5].map((m) => {
                    const val = row[`m${m}`] as number;
                    const opacity = Math.min(val / 100, 1);
                    return (
                      <td
                        key={m}
                        className="py-2 px-3 text-right font-mono text-xs"
                        style={{
                          backgroundColor: `rgba(217, 70, 239, ${opacity * 0.4})`,
                          color: val > 50 ? '#fff' : '#999',
                        }}
                      >
                        {val > 0 ? formatPct(val) : '—'}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* LTV by Gender */}
      <div>
        <SectionHeader title="LTV by Gender Segment" subtitle="Reinforcing the womenswear story — higher repeat, comparable AOV" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={ltvByGender} barGap={8}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="gender" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} tickFormatter={(v) => `£${v}`} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} formatter={(v: number) => typeof v === 'number' && v < 10 ? v.toFixed(1) : formatGBP(v)} />
              <Legend />
              <Bar dataKey="avgSpent" name="Avg LTV (£)" fill={ACCENT} radius={[4, 4, 0, 0]} />
              <Bar dataKey="repeatRate" name="Repeat Rate (%)" fill={ACCENT2} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Womens customers spend comparably and repeat more — the segment has product-market fit.</p>
        </div>
      </div>

      {/* LTV by Source */}
      <div>
        <SectionHeader title="LTV by Acquisition Source" subtitle="Average lifetime spend per customer by first-touch channel" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={ltvBySource}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="source" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} tickFormatter={(v) => `£${v}`} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} formatter={(v: number) => formatGBP(v)} />
              <Bar dataKey="avgSpent" name="Avg LTV" fill={ACCENT2} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Support Volume & Bot Resolution */}
      <div>
        <SectionHeader title="Support Volume & Resolution" subtitle="Monthly ticket volume and bot resolution rate" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={supportVolume}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 11 }} interval={2} />
              <YAxis tick={{ fill: '#999', fontSize: 11 }} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} />
              <Legend />
              <Bar dataKey="botResolved" name="Bot Resolved" stackId="a" fill={POSITIVE} />
              <Bar dataKey="humanResolved" name="Human Resolved" stackId="a" fill={MUTED} />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Bot handles ~40% of tickets — significant room for Fin AI to improve this to 60-70%.</p>
        </div>
      </div>

      {/* Bot Resolution Trend */}
      <div>
        <SectionHeader title="Bot Resolution Rate Trend" subtitle="Percentage of tickets resolved by bot over time" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={botResolutionTrend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 11 }} interval={2} />
              <YAxis tick={{ fill: '#999', fontSize: 11 }} tickFormatter={(v) => `${v}%`} domain={[0, 60]} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} formatter={(v: number) => formatPct(v)} />
              <Line type="monotone" dataKey="rate" stroke={ACCENT} strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Flat at ~40% — the Fin AI invitation. An upgrade here could cut human agent load by 30-50%.</p>
        </div>
      </div>

      {/* Category Breakdown */}
      <div>
        <SectionHeader title="Support Category Breakdown" subtitle="What customers complain about" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={supportCategories}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={120}
                label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#555' }}
              >
                {supportCategories.map((_, i) => (
                  <Cell key={i} fill={catColors[i % catColors.length]} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} />
            </PieChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Order status and sizing/fit dominate. Sizing is disproportionately womens — the gap Fin AI can close.</p>
        </div>
      </div>
    </div>
  );
}
