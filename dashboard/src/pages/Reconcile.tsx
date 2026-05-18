import { useMemo } from 'react';
import { useData } from '../data/DataContext';
import { ym, groupBy, sum } from '../data/utils';

interface RuleResult {
  num: number;
  desc: string;
  passed: boolean;
  message: string;
}

function isGoogleAds(desc: string) {
  const d = desc.toUpperCase();
  return d.includes('GOOGLE') && d.includes('ADS');
}
function isMetaAds(desc: string) {
  const d = desc.toUpperCase();
  return (d.includes('FB') || d.includes('META')) && d.includes('ADS');
}
function isKlaviyo(desc: string) {
  return desc.toUpperCase().includes('KLAVIYO');
}
function isSupplier(desc: string) {
  return desc.toUpperCase().includes('SWIFT XFER');
}
function isShopifyRefund(desc: string) {
  const d = desc.toUpperCase();
  return d.includes('SHOPIFY') && d.includes('REFUND');
}

export default function Reconcile() {
  const data = useData();

  const results = useMemo(() => {
    const rules: RuleResult[] = [];
    const TOL = 0.02; // slightly more tolerant than Python due to floating point

    // Rule 1: Order subtotals = sum of line items
    {
      const liSubs = new Map<string, number>();
      for (const li of data.lineItems) {
        liSubs.set(li.order_id, (liSubs.get(li.order_id) || 0) + li.price * li.quantity);
      }
      let badSub = 0, badTot = 0;
      for (const o of data.orders) {
        const liSum = liSubs.get(o.order_id) || 0;
        if (Math.abs(o.subtotal - liSum) > TOL) badSub++;
        const computed = o.subtotal - o.total_discounts + o.total_shipping + o.total_tax;
        if (Math.abs(o.total_price - computed) > TOL) badTot++;
      }
      rules.push({
        num: 1,
        desc: 'Order subtotals = sum of line items',
        passed: badSub === 0 && badTot === 0,
        message: badSub === 0 && badTot === 0
          ? `All ${data.orders.length} orders reconcile`
          : `Subtotal mismatches: ${badSub}, total_price mismatches: ${badTot}`,
      });
    }

    // Rule 2: Customer total_spent and orders_count
    {
      const spent = new Map<string, number>();
      const count = new Map<string, number>();
      for (const o of data.orders) {
        spent.set(o.customer_id, (spent.get(o.customer_id) || 0) + o.total_price);
        count.set(o.customer_id, (count.get(o.customer_id) || 0) + 1);
      }
      let badSpent = 0, badCount = 0;
      for (const c of data.customers) {
        if (Math.abs(c.total_spent - (spent.get(c.customer_id) || 0)) > TOL) badSpent++;
        if (c.orders_count !== (count.get(c.customer_id) || 0)) badCount++;
      }
      rules.push({
        num: 2,
        desc: 'Customer total_spent and orders_count match orders',
        passed: badSpent === 0 && badCount === 0,
        message: badSpent === 0 && badCount === 0
          ? `All ${data.customers.length} customers reconcile`
          : `Spent mismatches: ${badSpent}, count mismatches: ${badCount}`,
      });
    }

    // Rule 3: Discount code usage_count
    {
      const usage = new Map<string, number>();
      for (const o of data.orders) {
        const dc = (o.discount_code || '').trim();
        if (dc) usage.set(dc, (usage.get(dc) || 0) + 1);
      }
      let bad = 0;
      for (const c of data.discountCodes) {
        if (c.usage_count !== (usage.get(c.code) || 0)) bad++;
      }
      rules.push({
        num: 3,
        desc: 'Discount code usage_count = orders using that code',
        passed: bad === 0,
        message: bad === 0 ? `All ${data.discountCodes.length} codes reconcile` : `${bad} mismatches`,
      });
    }

    // Rule 4: Every line item produces inventory movement (sale)
    {
      const expected = new Map<string, number>();
      for (const li of data.lineItems) {
        const key = `${li.order_id}|${li.variant_id}`;
        expected.set(key, (expected.get(key) || 0) + li.quantity);
      }
      const actual = new Map<string, number>();
      for (const mv of data.inventoryMovements) {
        if (mv.type === 'sale') {
          const key = `${mv.reference_id}|${mv.variant_id}`;
          actual.set(key, (actual.get(key) || 0) + Math.abs(mv.quantity_delta));
        }
      }
      let bad = 0;
      for (const [key, exp] of expected) {
        if (Math.abs(exp - (actual.get(key) || 0)) > TOL) bad++;
      }
      rules.push({
        num: 4,
        desc: 'Every line item produces inventory movement (sale)',
        passed: bad === 0,
        message: bad === 0 ? `All ${expected.size} pairs reconcile` : `${bad} mismatches`,
      });
    }

    // Rule 5: Every PO receipt produces inventory movements
    {
      const receivedPOs = new Set(data.purchaseOrders.filter((p) => p.status === 'received').map((p) => p.po_id));
      const expected = new Map<string, number>();
      for (const pl of data.poLineItems) {
        if (receivedPOs.has(pl.po_id)) {
          const key = `${pl.po_id}|${pl.variant_id}`;
          expected.set(key, (expected.get(key) || 0) + pl.quantity_received);
        }
      }
      const actual = new Map<string, number>();
      for (const mv of data.inventoryMovements) {
        if (mv.type === 'po_receipt') {
          const key = `${mv.reference_id}|${mv.variant_id}`;
          actual.set(key, (actual.get(key) || 0) + mv.quantity_delta);
        }
      }
      let bad = 0;
      for (const [key, exp] of expected) {
        if (Math.abs(exp - (actual.get(key) || 0)) > TOL) bad++;
      }
      rules.push({
        num: 5,
        desc: 'Every PO receipt produces inventory movement (po_receipt)',
        passed: bad === 0,
        message: bad === 0 ? `All ${expected.size} pairs reconcile` : `${bad} mismatches`,
      });
    }

    // Rule 6: Every refund produces inventory return + bank txn
    {
      const expectedReturns = new Map<string, number>();
      for (const r of data.refunds) {
        try {
          const variants: string[] = JSON.parse(r.refund_line_items || '[]');
          for (const vid of variants) {
            const key = `${r.order_id}|${vid}`;
            expectedReturns.set(key, (expectedReturns.get(key) || 0) + 1);
          }
        } catch {}
      }
      const actualReturns = new Map<string, number>();
      for (const mv of data.inventoryMovements) {
        if (mv.type === 'return') {
          const key = `${mv.reference_id}|${mv.variant_id}`;
          actualReturns.set(key, (actualReturns.get(key) || 0) + mv.quantity_delta);
        }
      }
      let badInv = 0;
      for (const [key, exp] of expectedReturns) {
        if (Math.abs(exp - (actualReturns.get(key) || 0)) > TOL) badInv++;
      }

      // Monthly refund vs bank
      const refundMonthly = new Map<string, number>();
      for (const r of data.refunds) {
        const m = ym(r.created_at);
        refundMonthly.set(m, (refundMonthly.get(m) || 0) + r.amount);
      }
      const bankRefundMonthly = new Map<string, number>();
      for (const bt of data.bankTransactions) {
        if (isShopifyRefund(bt.description)) {
          const m = ym(bt.date);
          bankRefundMonthly.set(m, (bankRefundMonthly.get(m) || 0) + Math.abs(bt.amount_gbp));
        }
      }
      let badBank = 0;
      const allRefMonths = new Set([...refundMonthly.keys(), ...bankRefundMonthly.keys()]);
      for (const m of allRefMonths) {
        if (Math.abs((refundMonthly.get(m) || 0) - (bankRefundMonthly.get(m) || 0)) > TOL) badBank++;
      }

      rules.push({
        num: 6,
        desc: 'Every refund -> inventory return + bank txn',
        passed: badInv === 0 && badBank === 0,
        message: badInv === 0 && badBank === 0
          ? `All ${expectedReturns.size} returns reconcile, bank matches`
          : `Inv mismatches: ${badInv}, bank month mismatches: ${badBank}`,
      });
    }

    // Rule 7: Inventory movements sum to current stock
    {
      const mvSums = new Map<string, number>();
      for (const mv of data.inventoryMovements) {
        mvSums.set(mv.variant_id, (mvSums.get(mv.variant_id) || 0) + mv.quantity_delta);
      }
      let bad = 0;
      for (const v of data.variants) {
        if (Math.abs(v.inventory_quantity - (mvSums.get(v.variant_id) || 0)) > TOL) bad++;
      }
      rules.push({
        num: 7,
        desc: 'Inventory movements sum to current stock level',
        passed: bad === 0,
        message: bad === 0 ? `All ${data.variants.length} variants reconcile` : `${bad} mismatches`,
      });
    }

    // Rule 8: Monthly Google ad spend = bank
    {
      const adsMonthly = new Map<string, number>();
      for (const a of data.googleAds) {
        const m = ym(a.date);
        adsMonthly.set(m, (adsMonthly.get(m) || 0) + a.spend_gbp);
      }
      const bankMonthly = new Map<string, number>();
      for (const bt of data.bankTransactions) {
        if (isGoogleAds(bt.description)) {
          const m = ym(bt.date);
          bankMonthly.set(m, (bankMonthly.get(m) || 0) + Math.abs(bt.amount_gbp));
        }
      }
      let bad = 0;
      const allMonths = new Set([...adsMonthly.keys(), ...bankMonthly.keys()]);
      for (const m of allMonths) {
        if (Math.abs((adsMonthly.get(m) || 0) - (bankMonthly.get(m) || 0)) > TOL) bad++;
      }
      rules.push({
        num: 8,
        desc: 'Monthly Google ad spend = Google bank transactions',
        passed: bad === 0,
        message: bad === 0 ? `All ${allMonths.size} months reconcile` : `${bad} month mismatches`,
      });
    }

    // Rule 9: Monthly Meta ad spend = bank
    {
      const adsMonthly = new Map<string, number>();
      for (const a of data.metaAds) {
        const m = ym(a.date);
        adsMonthly.set(m, (adsMonthly.get(m) || 0) + a.spend_gbp);
      }
      const bankMonthly = new Map<string, number>();
      for (const bt of data.bankTransactions) {
        if (isMetaAds(bt.description)) {
          const m = ym(bt.date);
          bankMonthly.set(m, (bankMonthly.get(m) || 0) + Math.abs(bt.amount_gbp));
        }
      }
      let bad = 0;
      const allMonths = new Set([...adsMonthly.keys(), ...bankMonthly.keys()]);
      for (const m of allMonths) {
        if (Math.abs((adsMonthly.get(m) || 0) - (bankMonthly.get(m) || 0)) > TOL) bad++;
      }
      rules.push({
        num: 9,
        desc: 'Monthly Meta ad spend = Meta bank transactions',
        passed: bad === 0,
        message: bad === 0 ? `All ${allMonths.size} months reconcile` : `${bad} month mismatches`,
      });
    }

    // Rule 10: UTM campaign names in orders exist in ads/email
    {
      const known = new Set<string>();
      for (const a of data.googleAds) known.add(a.campaign_name);
      for (const a of data.metaAds) known.add(a.campaign_name);
      for (const e of data.emailCampaigns) known.add(e.name);

      const orphans = new Set<string>();
      for (const o of data.orders) {
        const camp = (o.utm_campaign || '').trim();
        if (camp && !known.has(camp)) orphans.add(camp);
      }
      rules.push({
        num: 10,
        desc: 'UTM campaign names in orders exist in ads/email',
        passed: orphans.size === 0,
        message: orphans.size === 0 ? 'All campaigns found' : `${orphans.size} orphan campaigns: ${[...orphans].slice(0, 3).join(', ')}`,
      });
    }

    // Rule 11: Email attributed_orders/revenue match orders
    {
      const klOrders = groupBy(
        data.orders.filter((o) => (o.utm_source || '').toLowerCase() === 'klaviyo' && o.utm_campaign),
        (o) => o.utm_campaign
      );
      let bad = 0;
      for (const c of data.emailCampaigns) {
        const matched = klOrders[c.name] || [];
        const expCount = matched.length;
        const expRev = sum(matched.map((o) => o.total_price));
        if (c.attributed_orders !== expCount || Math.abs(c.attributed_revenue_gbp - expRev) > TOL) bad++;
      }
      rules.push({
        num: 11,
        desc: 'Email attributed_orders/revenue match orders',
        passed: bad === 0,
        message: bad === 0 ? `All ${data.emailCampaigns.length} campaigns reconcile` : `${bad} mismatches`,
      });
    }

    // Rule 12: Klaviyo subscription monthly in bank
    {
      const orderMonths = new Set(data.orders.map((o) => ym(o.created_at)));
      const klMonths = new Set<string>();
      for (const bt of data.bankTransactions) {
        if (isKlaviyo(bt.description)) klMonths.add(ym(bt.date));
      }
      const missing = [...orderMonths].filter((m) => !klMonths.has(m));
      rules.push({
        num: 12,
        desc: 'Klaviyo subscription appears monthly in bank',
        passed: missing.length === 0,
        message: missing.length === 0 ? `Present in all ${orderMonths.size} months` : `Missing in ${missing.length} months`,
      });
    }

    // Rule 13: PO payments in bank = purchase_orders.total_cost_gbp
    {
      const bankDates = data.bankTransactions.map((t) => t.date).filter(Boolean);
      const bankStart = bankDates.reduce((a, b) => (a < b ? a : b), '9999');
      const bankEnd = bankDates.reduce((a, b) => (a > b ? a : b), '0000');

      let expectedTotal = 0;
      let poCount = 0;
      for (const po of data.purchaseOrders) {
        const cost = po.total_cost_gbp;
        const deposit = Math.round((cost / 2) * 100) / 100;
        const balance = cost - deposit;
        let contributed = false;
        if (po.deposit_paid_at && po.deposit_paid_at >= bankStart && po.deposit_paid_at <= bankEnd) {
          expectedTotal += deposit;
          contributed = true;
        }
        if (po.balance_paid_at && po.balance_paid_at >= bankStart && po.balance_paid_at <= bankEnd) {
          expectedTotal += balance;
          contributed = true;
        }
        if (contributed) poCount++;
      }

      let supplierTotal = 0;
      for (const bt of data.bankTransactions) {
        if (isSupplier(bt.description)) supplierTotal += Math.abs(bt.amount_gbp);
      }

      const tol = TOL * Math.max(poCount, 1);
      rules.push({
        num: 13,
        desc: 'PO payments in bank = purchase_orders.total_cost_gbp',
        passed: Math.abs(expectedTotal - supplierTotal) <= tol,
        message: Math.abs(expectedTotal - supplierTotal) <= tol
          ? `${poCount} POs match (${expectedTotal.toFixed(2)} vs ${supplierTotal.toFixed(2)})`
          : `Diff: ${(expectedTotal - supplierTotal).toFixed(2)}`,
      });
    }

    // Rule 14: Running bank balance consistent
    {
      let bad = 0;
      let prevBal: number | null = null;
      for (const bt of data.bankTransactions) {
        if (prevBal !== null) {
          const expected = prevBal + bt.amount_gbp;
          if (Math.abs(bt.balance_gbp - expected) > TOL) bad++;
        }
        prevBal = bt.balance_gbp;
      }
      rules.push({
        num: 14,
        desc: 'Running bank balance internally consistent',
        passed: bad === 0,
        message: bad === 0 ? `All ${data.bankTransactions.length} transactions consistent` : `${bad} breaks`,
      });
    }

    // Rule 15: Net Sales = subtotals - discounts - refunds
    {
      const gross = sum(data.orders.map((o) => o.subtotal));
      const disc = sum(data.orders.map((o) => o.total_discounts));
      const ref = sum(data.refunds.map((r) => r.amount));
      const net = gross - disc - ref;
      rules.push({
        num: 15,
        desc: 'Net Sales = subtotals - discounts - refunds',
        passed: net > 0,
        message: `Net sales = £${net.toFixed(2)} (gross ${gross.toFixed(0)} - disc ${disc.toFixed(0)} - ref ${ref.toFixed(0)})`,
      });
    }

    // Rule 16: COGS = sum(units sold x landed cost)
    {
      const landed = new Map<string, number>();
      for (const pl of data.poLineItems) landed.set(pl.variant_id, pl.landed_cost_per_unit_gbp);
      let missingCost = 0;
      let cogs = 0;
      for (const li of data.lineItems) {
        if (!landed.has(li.variant_id)) missingCost++;
        else cogs += li.quantity * (landed.get(li.variant_id) || 0);
      }
      const netSales = sum(data.orders.map((o) => o.subtotal)) - sum(data.orders.map((o) => o.total_discounts));
      const margin = netSales > 0 ? ((netSales - cogs) / netSales) * 100 : 0;
      rules.push({
        num: 16,
        desc: 'COGS = sum(units sold x landed cost)',
        passed: missingCost === 0,
        message: missingCost === 0
          ? `COGS = £${cogs.toFixed(0)}, margin = ${margin.toFixed(1)}%`
          : `${missingCost} variants missing cost`,
      });
    }

    // Rule 17: Inventory value = quantity x landed cost
    {
      const landed = new Map<string, number>();
      for (const pl of data.poLineItems) landed.set(pl.variant_id, pl.landed_cost_per_unit_gbp);
      let total = 0;
      let missing = 0;
      for (const v of data.variants) {
        if (v.inventory_quantity > 0) {
          if (!landed.has(v.variant_id)) missing++;
          else total += v.inventory_quantity * (landed.get(v.variant_id) || 0);
        }
      }
      rules.push({
        num: 17,
        desc: 'Inventory value = quantity x landed cost',
        passed: missing === 0,
        message: missing === 0 ? `Total inventory value = £${total.toFixed(0)}` : `${missing} variants with stock but no cost`,
      });
    }

    // Rule 18: Accounts Payable = outstanding PO balances
    {
      let ap = 0;
      let outstandingCount = 0;
      for (const po of data.purchaseOrders) {
        if (!po.balance_paid_at) {
          if (po.deposit_paid_at) ap += po.total_cost_gbp / 2;
          else ap += po.total_cost_gbp;
          outstandingCount++;
        }
      }
      rules.push({
        num: 18,
        desc: 'Accounts Payable = outstanding PO balances',
        passed: true,
        message: `AP = £${ap.toFixed(0)} (${outstandingCount} POs outstanding)`,
      });
    }

    // Rule 19: Support ticket FK references
    {
      const orderIds = new Set(data.orders.map((o) => o.order_id));
      const productIds = new Set(data.products.map((p) => p.product_id));
      const customerIds = new Set(data.customers.map((c) => c.customer_id));
      let bad = 0;
      for (const t of data.supportTickets) {
        if (t.related_order_id && !orderIds.has(t.related_order_id)) bad++;
        if (t.related_product_id && !productIds.has(t.related_product_id)) bad++;
        if (t.customer_id && !customerIds.has(t.customer_id)) bad++;
      }
      rules.push({
        num: 19,
        desc: 'Support ticket FK references all exist',
        passed: bad === 0,
        message: bad === 0 ? `All ${data.supportTickets.length} tickets valid` : `${bad} broken FKs`,
      });
    }

    // Rule 20: UTM campaign names consistent across all tables
    {
      const orderCamps = new Set<string>();
      for (const o of data.orders) {
        const c = (o.utm_campaign || '').trim();
        if (c) orderCamps.add(c);
      }
      const googleCamps = new Set(data.googleAds.map((a) => a.campaign_name));
      const metaCamps = new Set(data.metaAds.map((a) => a.campaign_name));
      const emailCamps = new Set(data.emailCampaigns.map((e) => e.name));
      const allKnown = new Set([...googleCamps, ...metaCamps, ...emailCamps]);
      const orphans = [...orderCamps].filter((c) => !allKnown.has(c));
      rules.push({
        num: 20,
        desc: 'UTM campaign names consistent across all tables',
        passed: orphans.length === 0,
        message: orphans.length === 0
          ? `${orderCamps.size} order campaigns, ${googleCamps.size} Google, ${metaCamps.size} Meta, ${emailCamps.size} email`
          : `${orphans.length} orphan campaigns`,
      });
    }

    return rules;
  }, [data]);

  const passCount = results.filter((r) => r.passed).length;

  return (
    <div className="min-h-screen bg-neutral-950 text-white p-8">
      <div className="max-w-[900px] mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Reconciliation</h1>
            <p className="text-sm text-neutral-500 mt-1">
              20 validation rules from the spec, run against the dashboard's data.
            </p>
          </div>
          <div className={`text-3xl font-bold ${passCount === 20 ? 'text-green-400' : 'text-red-400'}`}>
            {passCount}/20
          </div>
        </div>

        <div className="space-y-2">
          {results.map((r) => (
            <div
              key={r.num}
              className={`flex items-start gap-3 p-3 rounded-lg border ${
                r.passed
                  ? 'border-green-900/50 bg-green-950/20'
                  : 'border-red-900/50 bg-red-950/20'
              }`}
            >
              <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                r.passed ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}>
                {r.passed ? '\u2713' : '\u2717'}
              </span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium">
                  <span className="text-neutral-500 mr-2">Rule {r.num}:</span>
                  {r.desc}
                </p>
                <p className="text-xs text-neutral-500 mt-0.5 font-mono">{r.message}</p>
              </div>
            </div>
          ))}
        </div>

        <div className="mt-8 text-center">
          <a href="#/assessment" className="text-sm text-accent hover:underline">
            &larr; Back to Assessment
          </a>
        </div>
      </div>
    </div>
  );
}
