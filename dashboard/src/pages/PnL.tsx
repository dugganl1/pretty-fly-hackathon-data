import { useMemo, useState } from 'react';
import { useData } from '../data/DataContext';
import { formatGBP, ym, monthLabel, sum, groupBy } from '../data/utils';

interface PnLRow {
  label: string;
  current: number;
  prior?: number;
  isHeader?: boolean;
  isTotal?: boolean;
  indent?: number;
  annotation?: string;
}

export default function PnL() {
  const data = useData();

  const allMonths = useMemo(() => {
    const months = new Set<string>();
    data.orders.forEach((o) => months.add(ym(o.created_at)));
    return Array.from(months).sort();
  }, [data]);

  const [selectedMonth, setSelectedMonth] = useState(allMonths[allMonths.length - 1] || '');

  const pnl = useMemo(() => {
    if (!selectedMonth) return [];

    const monthOrders = data.orders.filter((o) => ym(o.created_at) === selectedMonth);
    const monthRefunds = data.refunds.filter((r) => ym(r.created_at) === selectedMonth);
    const monthBank = data.bankTransactions.filter((t) => ym(t.date) === selectedMonth);

    // Prior period (same month last year)
    const [y, m] = selectedMonth.split('-');
    const priorMonth = `${parseInt(y) - 1}-${m}`;
    const priorOrders = data.orders.filter((o) => ym(o.created_at) === priorMonth);
    const priorRefunds = data.refunds.filter((r) => ym(r.created_at) === priorMonth);
    const priorBank = data.bankTransactions.filter((t) => ym(t.date) === priorMonth);
    const hasPrior = priorOrders.length > 0;

    // Landed cost lookup
    const landedCost = new Map<string, number>();
    for (const pl of data.poLineItems) {
      landedCost.set(pl.variant_id, pl.landed_cost_per_unit_gbp);
    }

    const computeForPeriod = (orders: typeof data.orders, refunds: typeof data.refunds, bank: typeof data.bankTransactions) => {
      const grossSales = sum(orders.map((o) => o.subtotal));
      const discounts = sum(orders.map((o) => o.total_discounts));
      const refundTotal = sum(refunds.map((r) => r.amount));
      const netSales = grossSales - discounts - refundTotal;

      // COGS
      const orderIds = new Set(orders.map((o) => o.order_id));
      const monthLineItems = data.lineItems.filter((li) => orderIds.has(li.order_id));
      const cogs = sum(
        monthLineItems.map((li) => (landedCost.get(li.variant_id) || 0) * li.quantity)
      );
      const productMargin = netSales - cogs;

      // Bank-based costs
      const bankCats = (desc: string, rawCat: string) => {
        const d = desc.toUpperCase();
        return {
          isShipping: rawCat === '3PL' || rawCat === 'SHIPPING' || d.includes('HUB3PL') || d.includes('DHL') || d.includes('ROYAL MAIL'),
          isMerchantFee: rawCat === 'SHOPIFY_FEE' || (d.includes('SHOPIFY') && d.includes('FEE')),
          isGoogleAds: d.includes('GOOGLE') && d.includes('ADS'),
          isMetaAds: (d.includes('FB') || d.includes('META')) && d.includes('ADS'),
          isKlaviyo: d.includes('KLAVIYO'),
          isPayroll: rawCat === 'PAYROLL' || d.includes('PAYROLL'),
          isRent: rawCat === 'RENT' || d.includes('STANDING ORDER') || d.includes('STUDIO'),
          isSaas: rawCat === 'SAAS',
        };
      };

      let shipping = 0, merchantFees = 0, googleSpend = 0, metaSpend = 0, klaviyo = 0;
      let payroll = 0, rent = 0, saas = 0;

      for (const t of bank) {
        const cats = bankCats(t.description, t.raw_category);
        const amt = Math.abs(t.amount_gbp);
        if (cats.isShipping) shipping += amt;
        else if (cats.isMerchantFee) merchantFees += amt;
        else if (cats.isGoogleAds) googleSpend += amt;
        else if (cats.isMetaAds) metaSpend += amt;
        else if (cats.isKlaviyo) klaviyo += amt;
        else if (cats.isPayroll) payroll += amt;
        else if (cats.isRent) rent += amt;
        else if (cats.isSaas) saas += amt;
      }

      // Estimate merchant fees from orders if no bank data
      if (merchantFees === 0) {
        merchantFees = sum(orders.map((o) => o.total_price)) * 0.02;
      }

      const totalMarketing = googleSpend + metaSpend + klaviyo;
      const grossProfit = productMargin - shipping - merchantFees;
      const contributionProfit = grossProfit - totalMarketing;
      const operatingCosts = payroll + rent + saas;
      const operatingProfit = contributionProfit - operatingCosts;

      return {
        grossSales,
        discounts: discounts + refundTotal,
        netSales,
        cogs,
        productMargin,
        shipping,
        merchantFees,
        grossProfit,
        googleSpend,
        metaSpend,
        klaviyo,
        totalMarketing,
        contributionProfit,
        payroll,
        rent,
        saas,
        operatingCosts,
        operatingProfit,
      };
    };

    const current = computeForPeriod(monthOrders, monthRefunds, monthBank);
    const prior = hasPrior ? computeForPeriod(priorOrders, priorRefunds, priorBank) : null;

    const pctOfRev = (val: number) => current.netSales > 0 ? `${((val / current.netSales) * 100).toFixed(1)}% of net sales` : '';

    const rows: PnLRow[] = [
      { label: 'Gross Sales', current: current.grossSales, prior: prior?.grossSales, annotation: `${monthOrders.length} orders this month` },
      { label: 'Discounts & Returns', current: -current.discounts, prior: prior ? -prior.discounts : undefined, indent: 1 },
      { label: 'Net Sales', current: current.netSales, prior: prior?.netSales, isTotal: true },
      { label: 'Product Purchases (Landed)', current: -current.cogs, prior: prior ? -prior.cogs : undefined, indent: 1, annotation: pctOfRev(current.cogs) },
      { label: 'Product Margin', current: current.productMargin, prior: prior?.productMargin, isTotal: true, annotation: current.netSales > 0 ? `${((current.productMargin / current.netSales) * 100).toFixed(1)}% product margin` : '' },
      { label: 'Shipping & Fulfilment', current: -current.shipping, prior: prior ? -prior.shipping : undefined, indent: 1 },
      { label: 'Merchant & Payment Fees', current: -current.merchantFees, prior: prior ? -prior.merchantFees : undefined, indent: 1 },
      { label: 'Gross Profit', current: current.grossProfit, prior: prior?.grossProfit, isTotal: true, annotation: current.netSales > 0 ? `${((current.grossProfit / current.netSales) * 100).toFixed(1)}% gross margin` : '' },
      { label: 'Google Ads', current: -current.googleSpend, prior: prior ? -prior.googleSpend : undefined, indent: 1 },
      { label: 'Meta Ads', current: -current.metaSpend, prior: prior ? -prior.metaSpend : undefined, indent: 1 },
      { label: 'Klaviyo', current: -current.klaviyo, prior: prior ? -prior.klaviyo : undefined, indent: 1 },
      { label: 'Total Marketing', current: -current.totalMarketing, prior: prior ? -prior.totalMarketing : undefined, isTotal: true, annotation: pctOfRev(current.totalMarketing) },
      { label: 'Contribution Profit', current: current.contributionProfit, prior: prior?.contributionProfit, isTotal: true, annotation: current.netSales > 0 ? `${((current.contributionProfit / current.netSales) * 100).toFixed(1)}% contribution margin` : '' },
      { label: 'Salaries & Wages', current: -current.payroll, prior: prior ? -prior.payroll : undefined, indent: 1 },
      { label: 'Rent & Facilities', current: -current.rent, prior: prior ? -prior.rent : undefined, indent: 1 },
      { label: 'Software & Subscriptions', current: -current.saas, prior: prior ? -prior.saas : undefined, indent: 1, annotation: 'Includes Shopify, Fin/Intercom, Xero, Mixview...' },
      { label: 'Operating Costs', current: -current.operatingCosts, prior: prior ? -prior.operatingCosts : undefined, isTotal: true },
      { label: 'EBITDA', current: current.operatingProfit, prior: prior?.operatingProfit, isTotal: true, annotation: current.netSales > 0 ? `${((current.operatingProfit / current.netSales) * 100).toFixed(1)}% EBITDA margin` : '' },
    ];

    return rows;
  }, [data, selectedMonth]);

  // Trailing 12 months
  const t12 = useMemo(() => {
    const idx = allMonths.indexOf(selectedMonth);
    if (idx < 11) return null;
    return allMonths.slice(idx - 11, idx + 1);
  }, [allMonths, selectedMonth]);

  // Balance sheet items
  const balanceSheet = useMemo(() => {
    if (!selectedMonth) return null;
    const endOfMonth = `${selectedMonth}-31`;
    const bankAtMonth = data.bankTransactions.filter((t) => t.date <= endOfMonth);
    const cash = bankAtMonth.length > 0 ? bankAtMonth[bankAtMonth.length - 1].balance_gbp : 0;

    const landedCost = new Map<string, number>();
    for (const pl of data.poLineItems) landedCost.set(pl.variant_id, pl.landed_cost_per_unit_gbp);

    let inventoryValue = 0;
    for (const v of data.variants) {
      if (v.inventory_quantity > 0) {
        inventoryValue += v.inventory_quantity * (landedCost.get(v.variant_id) || 0);
      }
    }

    let ap = 0;
    for (const po of data.purchaseOrders) {
      if (!po.balance_paid_at || po.balance_paid_at > endOfMonth) {
        const cost = po.total_cost_gbp;
        if (po.deposit_paid_at && po.deposit_paid_at <= endOfMonth) {
          ap += cost / 2;
        } else if (!po.deposit_paid_at || po.deposit_paid_at > endOfMonth) {
          ap += cost;
        }
      }
    }

    return { cash, inventoryValue, ap };
  }, [data, selectedMonth]);

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight">Profit & Loss</h2>
          <p className="text-sm text-neutral-500 mt-1">
            Full monthly P&L with Wayflyer annotations. Select a month to view.
          </p>
        </div>
        <select
          value={selectedMonth}
          onChange={(e) => setSelectedMonth(e.target.value)}
          className="bg-surface border border-border rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-1 focus:ring-accent"
        >
          {allMonths.map((m) => (
            <option key={m} value={m}>
              {monthLabel(m)}
            </option>
          ))}
        </select>
      </div>

      {/* P&L Table */}
      <div className="bg-surface border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="text-left py-3 px-4 text-neutral-500 font-medium">Line Item</th>
              <th className="text-right py-3 px-4 text-neutral-500 font-medium">{monthLabel(selectedMonth)}</th>
              {pnl[0]?.prior !== undefined && (
                <th className="text-right py-3 px-4 text-neutral-500 font-medium">YoY</th>
              )}
              <th className="text-left py-3 px-4 text-neutral-500 font-medium w-[300px]">Wayflyer Note</th>
            </tr>
          </thead>
          <tbody>
            {pnl.map((row, i) => (
              <tr
                key={i}
                className={`border-b border-border/50 ${row.isTotal ? 'bg-surface-raised' : ''}`}
              >
                <td
                  className={`py-2.5 px-4 ${row.isTotal ? 'font-semibold text-white' : 'text-neutral-300'}`}
                  style={{ paddingLeft: `${(row.indent || 0) * 20 + 16}px` }}
                >
                  {row.label}
                </td>
                <td
                  className={`py-2.5 px-4 text-right font-mono ${
                    row.isTotal ? 'font-semibold text-white' : ''
                  } ${row.current < 0 ? 'text-neutral-400' : ''}`}
                >
                  {row.current < 0 ? `(${formatGBP(Math.abs(row.current))})` : formatGBP(row.current)}
                </td>
                {row.prior !== undefined && (
                  <td className="py-2.5 px-4 text-right font-mono text-neutral-500">
                    {row.prior < 0
                      ? `(${formatGBP(Math.abs(row.prior))})`
                      : formatGBP(row.prior)}
                  </td>
                )}
                {pnl[0]?.prior !== undefined && row.prior === undefined && (
                  <td className="py-2.5 px-4 text-right text-neutral-600">—</td>
                )}
                <td className="py-2.5 px-4 text-xs text-neutral-500">
                  {row.annotation || ''}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Balance Sheet Memo */}
      {balanceSheet && (
        <div className="mt-6 grid grid-cols-3 gap-4">
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Cash</p>
            <p className="text-xl font-bold text-white">{formatGBP(balanceSheet.cash)}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Inventory Value</p>
            <p className="text-xl font-bold text-white">{formatGBP(balanceSheet.inventoryValue)}</p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-4">
            <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Accounts Payable</p>
            <p className="text-xl font-bold text-white">{formatGBP(balanceSheet.ap)}</p>
          </div>
        </div>
      )}
    </div>
  );
}
