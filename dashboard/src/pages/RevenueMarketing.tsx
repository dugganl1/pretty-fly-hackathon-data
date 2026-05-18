import { useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Cell, LineChart, Line, Legend,
} from 'recharts';
import { useData } from '../data/DataContext';
import SectionHeader from '../components/SectionHeader';
import MetricCard from '../components/MetricCard';
import { formatGBP, formatPct, ym, monthLabel, sum, groupBy } from '../data/utils';

const ACCENT = '#d946ef';
const ACCENT2 = '#8b5cf6';
const MUTED = '#525252';
const POSITIVE = '#22c55e';

export default function RevenueMarketing() {
  const data = useData();

  // Monthly revenue
  const monthlyRevenue = useMemo(() => {
    const byMonth = groupBy(data.orders, (o) => ym(o.created_at));
    return Object.entries(byMonth)
      .map(([month, orders]) => ({
        month,
        label: monthLabel(month),
        revenue: sum(orders.map((o) => o.total_price)),
        orders: orders.length,
        aov: orders.length > 0 ? sum(orders.map((o) => o.total_price)) / orders.length : 0,
      }))
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [data]);

  // Channel mix
  const channelMix = useMemo(() => {
    const byMonth = groupBy(data.orders, (o) => ym(o.created_at));
    const months = Object.keys(byMonth).sort();
    return months.map((month) => {
      const orders = byMonth[month];
      const bySource = groupBy(orders, (o) => o.utm_source || 'direct');
      const row: Record<string, number | string> = { month, label: monthLabel(month) };
      for (const [source, ords] of Object.entries(bySource)) {
        row[source] = sum(ords.map((o) => o.total_price));
      }
      return row;
    });
  }, [data]);

  const channelNames = useMemo(() => {
    const sources = new Set<string>();
    data.orders.forEach((o) => sources.add(o.utm_source || 'direct'));
    return Array.from(sources).sort();
  }, [data]);

  const channelColors: Record<string, string> = {
    google: '#4285F4',
    facebook: '#E1306C',
    instagram: '#C13584',
    klaviyo: '#00B2A9',
    direct: '#999',
    organic: '#22c55e',
  };

  // Mens vs Womens since Dec 2025
  const genderSplit = useMemo(() => {
    const productMap = new Map(data.products.map((p) => [p.product_id, p]));
    const liWithGender = data.lineItems.map((li) => ({
      ...li,
      gender: productMap.get(li.product_id)?.gender_segment || 'unknown',
    }));
    const orderMonth = new Map(data.orders.map((o) => [o.order_id, ym(o.created_at)]));

    const byMonth: Record<string, { mens: number; womens: number }> = {};
    for (const li of liWithGender) {
      const month = orderMonth.get(li.order_id) || '';
      if (month < '2025-12') continue;
      if (!byMonth[month]) byMonth[month] = { mens: 0, womens: 0 };
      const rev = li.price * li.quantity;
      if (li.gender === 'womens') byMonth[month].womens += rev;
      else byMonth[month].mens += rev;
    }

    return Object.entries(byMonth)
      .map(([month, vals]) => ({ month, label: monthLabel(month), ...vals }))
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [data]);

  // ROAS by campaign (Google + Meta)
  const campaignROAS = useMemo(() => {
    const googleBycamp = groupBy(data.googleAds, (a) => a.campaign_name);
    const metaBycamp = groupBy(data.metaAds, (a) => a.campaign_name);

    const campaigns = [
      ...Object.entries(googleBycamp).map(([name, rows]) => ({
        name,
        platform: 'Google',
        spend: sum(rows.map((r) => r.spend_gbp)),
        platformRev: sum(rows.map((r) => r.conversion_value_gbp)),
        platformConv: sum(rows.map((r) => r.conversions)),
      })),
      ...Object.entries(metaBycamp).map(([name, rows]) => ({
        name,
        platform: 'Meta',
        spend: sum(rows.map((r) => r.spend_gbp)),
        platformRev: sum(rows.map((r) => r.conversion_value_gbp)),
        platformConv: sum(rows.map((r) => r.conversions)),
      })),
    ];

    // Shopify-attributed revenue per campaign
    const ordersByCamp = groupBy(
      data.orders.filter((o) => o.utm_campaign),
      (o) => o.utm_campaign
    );

    return campaigns
      .map((c) => {
        const shopifyOrders = ordersByCamp[c.name] || [];
        const shopifyRev = sum(shopifyOrders.map((o) => o.total_price));
        return {
          ...c,
          shopifyRev,
          shopifyOrders: shopifyOrders.length,
          platformROAS: c.spend > 0 ? c.platformRev / c.spend : 0,
          shopifyROAS: c.spend > 0 ? shopifyRev / c.spend : 0,
        };
      })
      .sort((a, b) => b.spend - a.spend);
  }, [data]);

  // CAC by acquisition source
  const cacBySource = useMemo(() => {
    const allGoogleSpend = sum(data.googleAds.map((a) => a.spend_gbp));
    const allMetaSpend = sum(data.metaAds.map((a) => a.spend_gbp));
    const klaviyoSpend = sum(
      data.bankTransactions
        .filter((t) => t.description.toUpperCase().includes('KLAVIYO'))
        .map((t) => Math.abs(t.amount_gbp))
    );

    const custBySource = groupBy(data.customers, (c) => {
      const src = (c.acquisition_source || '').split('/')[0];
      return src || 'direct';
    });

    return [
      { source: 'Google', spend: allGoogleSpend, customers: (custBySource['google'] || []).length },
      { source: 'Meta (FB/IG)', spend: allMetaSpend, customers: (custBySource['facebook'] || []).length + (custBySource['instagram'] || []).length },
      { source: 'Klaviyo', spend: klaviyoSpend, customers: (custBySource['klaviyo'] || []).length },
      { source: 'Direct/Organic', spend: 0, customers: (custBySource['direct'] || []).length + (custBySource['organic'] || []).length },
    ].map((s) => ({
      ...s,
      cac: s.customers > 0 ? s.spend / s.customers : 0,
    }));
  }, [data]);

  // Top-line metrics
  const totals = useMemo(() => {
    const totalRevenue = sum(data.orders.map((o) => o.total_price));
    const totalOrders = data.orders.length;
    const y1 = sum(data.orders.filter((o) => ym(o.created_at) < '2025-06').map((o) => o.total_price));
    const y2 = sum(data.orders.filter((o) => ym(o.created_at) >= '2025-06').map((o) => o.total_price));
    const yoyGrowth = y1 > 0 ? ((y2 - y1) / y1) * 100 : 0;
    const totalAdSpend = sum(data.googleAds.map((a) => a.spend_gbp)) + sum(data.metaAds.map((a) => a.spend_gbp));
    const blendedROAS = totalAdSpend > 0 ? totalRevenue / totalAdSpend : 0;
    return { totalRevenue, totalOrders, yoyGrowth, totalAdSpend, blendedROAS, aov: totalRevenue / totalOrders };
  }, [data]);

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Revenue & Marketing</h2>
        <p className="text-sm text-neutral-500 mt-1">Where revenue comes from and where ad spend goes.</p>
      </div>

      {/* Top metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Total Revenue" value={formatGBP(totals.totalRevenue)} subtitle="24 months" />
        <MetricCard label="YoY Growth" value={formatPct(totals.yoyGrowth)} trend={totals.yoyGrowth > 0 ? 'up' : 'down'} trendValue={totals.yoyGrowth > 0 ? 'Growing' : 'Declining'} />
        <MetricCard label="Total Ad Spend" value={formatGBP(totals.totalAdSpend)} subtitle={`Blended ROAS ${totals.blendedROAS.toFixed(1)}x`} />
        <MetricCard label="AOV" value={formatGBP(totals.aov)} subtitle={`${totals.totalOrders.toLocaleString()} orders`} />
      </div>

      {/* Monthly Revenue */}
      <div>
        <SectionHeader title="Monthly Revenue" subtitle="Revenue and order volume over 24 months" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={monthlyRevenue}>
              <defs>
                <linearGradient id="revGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={ACCENT} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={ACCENT} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 11 }} interval={2} />
              <YAxis tick={{ fill: '#999', fontSize: 11 }} tickFormatter={(v) => `£${(v / 1000).toFixed(0)}k`} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} formatter={(v: number) => formatGBP(v)} />
              <Area type="monotone" dataKey="revenue" stroke={ACCENT} fill="url(#revGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Clear seasonal peaks around drops and gifting season (Nov-Dec).</p>
        </div>
      </div>

      {/* Channel Mix */}
      <div>
        <SectionHeader title="Channel Mix" subtitle="Revenue by acquisition channel over time" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={channelMix}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 11 }} interval={2} />
              <YAxis tick={{ fill: '#999', fontSize: 11 }} tickFormatter={(v) => `£${(v / 1000).toFixed(0)}k`} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} />
              {channelNames.map((ch) => (
                <Area
                  key={ch}
                  type="monotone"
                  dataKey={ch}
                  stackId="1"
                  stroke={channelColors[ch] || '#666'}
                  fill={channelColors[ch] || '#666'}
                  fillOpacity={0.6}
                />
              ))}
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Meta (Facebook/Instagram) and direct are the dominant channels. Google growing steadily.</p>
        </div>
      </div>

      {/* Gender Split */}
      <div>
        <SectionHeader title="Mens vs Womens Revenue" subtitle="Since womenswear launch (Dec 2025)" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={genderSplit}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 11 }} />
              <YAxis tick={{ fill: '#999', fontSize: 11 }} tickFormatter={(v) => `£${(v / 1000).toFixed(0)}k`} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} formatter={(v: number) => formatGBP(v)} />
              <Legend />
              <Bar dataKey="mens" name="Mens" fill={MUTED} stackId="a" />
              <Bar dataKey="womens" name="Womens" fill={ACCENT} stackId="a" />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Womens is a small but growing share of revenue since Dec 2025 launch.</p>
        </div>
      </div>

      {/* ROAS by Campaign */}
      <div>
        <SectionHeader title="Campaign ROAS" subtitle="Platform-reported vs Shopify-attributed, sorted by spend" />
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Campaign</th>
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Platform</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Spend</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Platform ROAS</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Shopify ROAS</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Shopify Orders</th>
              </tr>
            </thead>
            <tbody>
              {campaignROAS.map((c, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-surface-hover">
                  <td className="py-2 px-4 text-white font-mono text-xs">{c.name}</td>
                  <td className="py-2 px-4 text-neutral-400">{c.platform}</td>
                  <td className="py-2 px-4 text-right font-mono">{formatGBP(c.spend)}</td>
                  <td className={`py-2 px-4 text-right font-mono ${c.platformROAS < 2 ? 'text-red-400' : 'text-green-400'}`}>
                    {c.platformROAS.toFixed(1)}x
                  </td>
                  <td className={`py-2 px-4 text-right font-mono ${c.shopifyROAS < 2 ? 'text-red-400' : 'text-green-400'}`}>
                    {c.shopifyROAS.toFixed(1)}x
                  </td>
                  <td className="py-2 px-4 text-right font-mono text-neutral-400">{c.shopifyOrders.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-neutral-500 mt-2">Generic_Streetwear_UK stands out with a sub-2x ROAS — well below the threshold where marketing pays for itself after fulfilment.</p>
      </div>

      {/* CAC by Source */}
      <div>
        <SectionHeader title="Customer Acquisition Cost" subtitle="Blended CAC by acquisition channel" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={cacBySource}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="source" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} tickFormatter={(v) => `£${v}`} />
              <Tooltip contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }} formatter={(v: number) => formatGBP(v)} />
              <Bar dataKey="cac" name="CAC" fill={ACCENT2} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Meta delivers the most customers but at the highest paid CAC. Direct/organic is effectively free acquisition.</p>
        </div>
      </div>
    </div>
  );
}
