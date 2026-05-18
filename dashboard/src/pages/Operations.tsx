import { useMemo } from 'react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, BarChart, Bar, Cell, Legend, AreaChart, Area,
} from 'recharts';
import { useData } from '../data/DataContext';
import SectionHeader from '../components/SectionHeader';
import MetricCard from '../components/MetricCard';
import { formatGBP, formatPct, ym, monthLabel, sum, groupBy } from '../data/utils';

const ACCENT = '#d946ef';
const WARNING = '#f59e0b';
const NEGATIVE = '#ef4444';
const POSITIVE = '#22c55e';
const MUTED = '#525252';

export default function Operations() {
  const data = useData();

  // Inventory health by product type
  const inventoryHealth = useMemo(() => {
    const productMap = new Map(data.products.map((p) => [p.product_id, p]));
    const landedCost = new Map<string, number>();
    for (const pl of data.poLineItems) landedCost.set(pl.variant_id, pl.landed_cost_per_unit_gbp);

    const soldByVariant = new Map<string, number>();
    for (const li of data.lineItems) {
      soldByVariant.set(li.variant_id, (soldByVariant.get(li.variant_id) || 0) + li.quantity);
    }

    // Group by product type + gender
    const groups: Record<string, { qty: number; value: number; sold: number; count: number }> = {};
    for (const v of data.variants) {
      const product = productMap.get(v.product_id);
      if (!product) continue;
      const key = `${product.gender_segment} ${product.product_type}`;
      if (!groups[key]) groups[key] = { qty: 0, value: 0, sold: 0, count: 0 };
      const qty = Math.max(0, v.inventory_quantity);
      groups[key].qty += qty;
      groups[key].value += qty * (landedCost.get(v.variant_id) || 0);
      groups[key].sold += soldByVariant.get(v.variant_id) || 0;
      groups[key].count++;
    }

    return Object.entries(groups)
      .map(([key, vals]) => ({
        category: key,
        ...vals,
        dio: vals.sold > 0 ? Math.round((vals.qty * 730) / vals.sold) : 9999,
      }))
      .sort((a, b) => b.dio - a.dio);
  }, [data]);

  // Cash position over time
  const cashOverTime = useMemo(() => {
    const byMonth: Record<string, number> = {};
    let lastBalanceByMonth: Record<string, number> = {};
    for (const t of data.bankTransactions) {
      const month = ym(t.date);
      lastBalanceByMonth[month] = t.balance_gbp;
    }
    return Object.entries(lastBalanceByMonth)
      .map(([month, balance]) => ({
        month,
        label: monthLabel(month),
        balance,
      }))
      .sort((a, b) => a.month.localeCompare(b.month));
  }, [data]);

  // PO deposits annotated on cash chart
  const poEvents = useMemo(() => {
    return data.purchaseOrders.map((po) => ({
      po_id: po.po_id,
      deposit_date: po.deposit_paid_at,
      balance_date: po.balance_paid_at,
      delivery_date: po.actual_delivery,
      total_gbp: po.total_cost_gbp,
      supplier: data.suppliers.find((s) => s.supplier_id === po.supplier_id)?.name || po.supplier_id,
    }));
  }, [data]);

  // Upcoming supplier payments (next 90 days from dataset end)
  const upcomingPayments = useMemo(() => {
    const datasetEnd = '2026-05-31';
    const futureDate = '2026-08-31';
    return data.purchaseOrders
      .filter((po) => {
        return (
          (po.deposit_paid_at && po.deposit_paid_at > datasetEnd && po.deposit_paid_at <= futureDate) ||
          (po.balance_paid_at && po.balance_paid_at > datasetEnd && po.balance_paid_at <= futureDate) ||
          (!po.balance_paid_at && po.status !== 'received')
        );
      })
      .map((po) => ({
        ...po,
        supplier: data.suppliers.find((s) => s.supplier_id === po.supplier_id)?.name || po.supplier_id,
      }));
  }, [data]);

  // PO lifecycle
  const poLifecycle = useMemo(() => {
    return data.purchaseOrders
      .sort((a, b) => a.created_at.localeCompare(b.created_at))
      .map((po) => {
        const supplier = data.suppliers.find((s) => s.supplier_id === po.supplier_id);
        const poLines = data.poLineItems.filter((pl) => pl.po_id === po.po_id);
        const variantIds = new Set(poLines.map((pl) => pl.variant_id));
        const revenueFromPO = sum(
          data.lineItems
            .filter((li) => variantIds.has(li.variant_id))
            .map((li) => li.price * li.quantity)
        );
        return {
          po_id: po.po_id,
          supplier: supplier?.name || po.supplier_id,
          created: po.created_at.slice(0, 10),
          delivery: po.actual_delivery,
          cost_gbp: po.total_cost_gbp,
          deposit_date: po.deposit_paid_at,
          balance_date: po.balance_paid_at,
          revenue_earned: revenueFromPO,
          roi: po.total_cost_gbp > 0 ? revenueFromPO / po.total_cost_gbp : 0,
          status: po.status,
        };
      });
  }, [data]);

  // Key metrics
  const metrics = useMemo(() => {
    const totalInventoryValue = sum(
      data.variants
        .filter((v) => v.inventory_quantity > 0)
        .map((v) => {
          const cost = data.poLineItems.find((pl) => pl.variant_id === v.variant_id)?.landed_cost_per_unit_gbp || 0;
          return v.inventory_quantity * cost;
        })
    );
    const cash = cashOverTime.length > 0 ? cashOverTime[cashOverTime.length - 1].balance : 0;
    const totalCOGS = sum(
      data.lineItems.map((li) => {
        const cost = data.poLineItems.find((pl) => pl.variant_id === li.variant_id)?.landed_cost_per_unit_gbp || 0;
        return cost * li.quantity;
      })
    );
    const avgInventory = totalInventoryValue;
    const turnover = avgInventory > 0 ? totalCOGS / avgInventory : 0;
    const dio = turnover > 0 ? 365 / turnover : 0;

    return { totalInventoryValue, cash, turnover, dio };
  }, [data, cashOverTime]);

  return (
    <div className="space-y-10">
      <div>
        <h2 className="text-2xl font-bold text-white tracking-tight">Operations</h2>
        <p className="text-sm text-neutral-500 mt-1">Inventory, cash conversion, suppliers. The Wayflyer-native view.</p>
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Cash Position" value={formatGBP(metrics.cash)} subtitle="End of dataset" />
        <MetricCard label="Inventory Value" value={formatGBP(metrics.totalInventoryValue)} subtitle="At landed cost" />
        <MetricCard label="Inventory Turnover" value={`${metrics.turnover.toFixed(1)}x`} subtitle="Annual" />
        <MetricCard label="Days Inventory Outstanding" value={`${Math.round(metrics.dio)}`} subtitle="Portfolio average" />
      </div>

      {/* Inventory Health Table */}
      <div>
        <SectionHeader title="Inventory Health" subtitle="DIO by category — flagging slow movers" />
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Category</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Units in Stock</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Value (Landed)</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Units Sold</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">DIO</th>
              </tr>
            </thead>
            <tbody>
              {inventoryHealth.map((row, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-surface-hover">
                  <td className="py-2 px-4 text-white">{row.category}</td>
                  <td className="py-2 px-4 text-right font-mono text-neutral-300">{row.qty.toLocaleString()}</td>
                  <td className="py-2 px-4 text-right font-mono text-neutral-300">{formatGBP(row.value)}</td>
                  <td className="py-2 px-4 text-right font-mono text-neutral-300">{row.sold.toLocaleString()}</td>
                  <td className={`py-2 px-4 text-right font-mono font-semibold ${
                    row.dio > 180 ? 'text-red-400' : row.dio > 90 ? 'text-yellow-400' : 'text-green-400'
                  }`}>
                    {row.dio > 999 ? '999+' : row.dio}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="text-xs text-neutral-500 mt-2">Womens categories show elevated DIO — initial buy was too aggressive on certain colourways.</p>
      </div>

      {/* Cash Position */}
      <div>
        <SectionHeader title="Cash Position" subtitle="Monthly closing balance with PO deposit moments" />
        <div className="bg-surface border border-border rounded-lg p-6">
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={cashOverTime}>
              <defs>
                <linearGradient id="cashGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={POSITIVE} stopOpacity={0.3} />
                  <stop offset="95%" stopColor={POSITIVE} stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 11 }} interval={2} />
              <YAxis tick={{ fill: '#999', fontSize: 11 }} tickFormatter={(v) => `£${(v / 1000).toFixed(0)}k`} />
              <Tooltip
                contentStyle={{ background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' }}
                formatter={(v: number) => formatGBP(v)}
              />
              <Area type="monotone" dataKey="balance" stroke={POSITIVE} fill="url(#cashGrad)" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
          <p className="text-xs text-neutral-500 mt-2">Cash dips correspond to PO deposit payments — the cash conversion cycle made visible.</p>
        </div>
      </div>

      {/* PO Lifecycle */}
      <div>
        <SectionHeader title="Purchase Order Lifecycle" subtitle="Deposit → Balance → Delivery → Revenue earned" />
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">PO</th>
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Supplier</th>
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Deposit</th>
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Balance</th>
                <th className="text-left py-3 px-4 text-neutral-500 font-medium">Delivery</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Cost</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">Revenue</th>
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">ROI</th>
              </tr>
            </thead>
            <tbody>
              {poLifecycle.map((po, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-surface-hover">
                  <td className="py-2 px-4 font-mono text-xs text-white">{po.po_id}</td>
                  <td className="py-2 px-4 text-neutral-300">{po.supplier}</td>
                  <td className="py-2 px-4 text-neutral-400 text-xs">{po.deposit_date || '—'}</td>
                  <td className="py-2 px-4 text-neutral-400 text-xs">{po.balance_date || '—'}</td>
                  <td className="py-2 px-4 text-neutral-400 text-xs">{po.delivery || '—'}</td>
                  <td className="py-2 px-4 text-right font-mono">{formatGBP(po.cost_gbp)}</td>
                  <td className="py-2 px-4 text-right font-mono text-green-400">{formatGBP(po.revenue_earned)}</td>
                  <td className={`py-2 px-4 text-right font-mono font-semibold ${po.roi > 2 ? 'text-green-400' : po.roi > 1 ? 'text-yellow-400' : 'text-red-400'}`}>
                    {po.roi.toFixed(1)}x
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
