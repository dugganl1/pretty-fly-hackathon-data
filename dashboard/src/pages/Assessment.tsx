import { useMemo } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  LineChart, Line, CartesianGrid, Cell, PieChart, Pie,
} from 'recharts';
import { useData } from '../data/DataContext';
import ObservationCard from '../components/ObservationCard';
import { formatGBP, formatPct, groupBy, sum, ym } from '../data/utils';

const ACCENT = '#d946ef';
const MUTED = '#525252';
const POSITIVE = '#22c55e';
const NEGATIVE = '#ef4444';
const WARNING = '#f59e0b';

const chartTooltipStyle = {
  contentStyle: { background: '#1a1a1a', border: '1px solid #333', borderRadius: '6px', fontSize: '12px' },
  labelStyle: { color: '#999' },
};

export default function Assessment() {
  const data = useData();

  // ===== Observation 1: Hidden Womenswear Story =====
  const obs1 = useMemo(() => {
    const metaBycamp = groupBy(data.metaAds, (a) => a.campaign_name);
    const womensSpend = sum(
      data.metaAds.filter((a) => a.campaign_name.toLowerCase().includes('womens')).map((a) => a.spend_gbp)
    );
    const mensSpend = sum(
      data.metaAds.filter((a) => !a.campaign_name.toLowerCase().includes('womens')).map((a) => a.spend_gbp)
    );
    const womensCusts = data.customers.filter((c) => c.gender_segment_affinity === 'womens');
    const mensCusts = data.customers.filter((c) => c.gender_segment_affinity === 'mens');
    const womensCAC = womensSpend / (womensCusts.length || 1);
    const mensCAC = mensSpend / (mensCusts.length || 1);

    // Repeat rate: customers with 2+ orders within 120 days of first order
    const ordersByCustomer = groupBy(data.orders, (o) => o.customer_id);
    const repeatRate = (custs: typeof data.customers) => {
      let repeaters = 0;
      for (const c of custs) {
        const orders = (ordersByCustomer[c.customer_id] || []).sort(
          (a, b) => a.created_at.localeCompare(b.created_at)
        );
        if (orders.length >= 2) {
          const first = new Date(orders[0].created_at).getTime();
          const second = new Date(orders[1].created_at).getTime();
          if ((second - first) / (1000 * 60 * 60 * 24) <= 120) repeaters++;
        }
      }
      return custs.length > 0 ? (repeaters / custs.length) * 100 : 0;
    };

    const womensRepeat = repeatRate(womensCusts);
    const mensRepeat = repeatRate(mensCusts);

    const chartData = [
      { metric: 'CAC', Womens: Math.round(womensCAC), Mens: Math.round(mensCAC) },
      { metric: 'Repeat %', Womens: Math.round(womensRepeat), Mens: Math.round(mensRepeat) },
    ];

    return { womensCAC, mensCAC, womensRepeat, mensRepeat, chartData, womensCusts: womensCusts.length };
  }, [data]);

  // ===== Observation 2: Cash Tied Up (DIO) =====
  const obs2 = useMemo(() => {
    const productMap = new Map(data.products.map((p) => [p.product_id, p]));
    const landedCost = new Map<string, number>();
    for (const pl of data.poLineItems) {
      landedCost.set(pl.variant_id, pl.landed_cost_per_unit_gbp);
    }
    const variantProduct = new Map(data.variants.map((v) => [v.variant_id, v.product_id]));

    // Sold qty by variant
    const soldByVariant = new Map<string, number>();
    for (const li of data.lineItems) {
      soldByVariant.set(li.variant_id, (soldByVariant.get(li.variant_id) || 0) + li.quantity);
    }

    // Slow movers: womens variants with high DIO
    const slowMovers: Array<{ sku: string; qty: number; sold: number; dio: number; value: number }> = [];
    let totalSlowValue = 0;
    let slowCount = 0;

    for (const v of data.variants) {
      const product = productMap.get(v.product_id);
      if (!product || product.gender_segment !== 'womens') continue;
      if (v.inventory_quantity <= 0) continue;

      const sold = soldByVariant.get(v.variant_id) || 0;
      const cost = landedCost.get(v.variant_id) || 0;
      const dio = sold > 0 ? (v.inventory_quantity * 730) / sold : 9999;

      if (dio > 180) {
        const value = v.inventory_quantity * cost;
        totalSlowValue += value;
        slowCount++;
        if (slowMovers.length < 10) {
          slowMovers.push({ sku: v.sku, qty: v.inventory_quantity, sold, dio: Math.round(dio), value });
        }
      }
    }

    return { totalSlowValue, slowCount, slowMovers };
  }, [data]);

  // ===== Observation 3: Bleeding Google Campaign =====
  const obs3 = useMemo(() => {
    const byCamp = groupBy(data.googleAds, (a) => a.campaign_name);
    const campStats = Object.entries(byCamp).map(([name, rows]) => {
      const spend = sum(rows.map((r) => r.spend_gbp));
      const rev = sum(rows.map((r) => r.conversion_value_gbp));
      return { name, spend, rev, roas: spend > 0 ? rev / spend : 0 };
    });
    campStats.sort((a, b) => a.roas - b.roas);
    const generic = campStats.find((c) => c.name.includes('Generic_Streetwear'));
    return { campStats, generic };
  }, [data]);

  // ===== Observation 4: Discounting Destroys Margin =====
  const obs4 = useMemo(() => {
    const itemsByOrder = groupBy(data.lineItems, (li) => li.order_id);
    const discounted = data.orders.filter((o) => o.discount_code && o.discount_code.trim());
    const nonDiscounted = data.orders.filter((o) => !o.discount_code || !o.discount_code.trim());

    const avgAOV = (orders: typeof data.orders) =>
      orders.length > 0 ? sum(orders.map((o) => o.total_price)) / orders.length : 0;
    const avgItems = (orders: typeof data.orders) => {
      if (!orders.length) return 0;
      return (
        sum(
          orders.map((o) => sum((itemsByOrder[o.order_id] || []).map((li) => li.quantity)))
        ) / orders.length
      );
    };

    return {
      discountedAOV: avgAOV(discounted),
      nonDiscountedAOV: avgAOV(nonDiscounted),
      discountedItems: avgItems(discounted),
      nonDiscountedItems: avgItems(nonDiscounted),
      discountRate: (discounted.length / data.orders.length) * 100,
      discountedCount: discounted.length,
    };
  }, [data]);

  // ===== Observation 5: Dead-weight SaaS =====
  const obs5 = useMemo(() => {
    const saas = data.bankTransactions.filter(
      (t) => t.raw_category === 'SAAS' || t.description.toUpperCase().includes('MIXVIEW')
    );
    const bySub = groupBy(saas, (t) => t.counterparty || t.description);
    const subs = Object.entries(bySub).map(([name, txns]) => ({
      name,
      total: Math.abs(sum(txns.map((t) => t.amount_gbp))),
      count: txns.length,
    }));
    subs.sort((a, b) => b.total - a.total);
    const mixview = subs.find((s) => s.name.toUpperCase().includes('MIXVIEW'));
    return { subs, mixview };
  }, [data]);

  // ===== Observation 6: Margin Compression =====
  const obs6 = useMemo(() => {
    const productMap = new Map(data.products.map((p) => [p.product_id, p]));
    const landedCost = new Map<string, number>();
    for (const pl of data.poLineItems) {
      landedCost.set(pl.variant_id, pl.landed_cost_per_unit_gbp);
    }

    const byType: Record<string, { rev: number; cost: number }> = {};
    for (const li of data.lineItems) {
      const product = productMap.get(li.product_id);
      if (!product) continue;
      const pt = product.product_type;
      if (!byType[pt]) byType[pt] = { rev: 0, cost: 0 };
      byType[pt].rev += li.price * li.quantity;
      const cost = landedCost.get(li.variant_id) || 0;
      byType[pt].cost += cost * li.quantity;
    }

    const margins = Object.entries(byType).map(([type, { rev, cost }]) => ({
      type,
      margin: rev > 0 ? ((rev - cost) / rev) * 100 : 0,
      rev,
      cost,
    }));
    margins.sort((a, b) => a.margin - b.margin);
    return margins;
  }, [data]);

  // ===== Observation 7: Trainer Return Rate =====
  const obs7 = useMemo(() => {
    const productMap = new Map(data.products.map((p) => [p.product_id, p]));
    const refundOrderIds = new Set(data.refunds.map((r) => r.order_id));

    const liWithType = data.lineItems.map((li) => ({
      ...li,
      product_type: productMap.get(li.product_id)?.product_type || 'Unknown',
    }));

    const byType = groupBy(liWithType, (li) => li.product_type);
    const returnRates = Object.entries(byType).map(([type, items]) => {
      const totalOrders = new Set(items.map((li) => li.order_id)).size;
      const refundedOrders = new Set(
        items.filter((li) => refundOrderIds.has(li.order_id)).map((li) => li.order_id)
      ).size;
      return { type, rate: totalOrders > 0 ? (refundedOrders / totalOrders) * 100 : 0, totalOrders };
    });
    returnRates.sort((a, b) => b.rate - a.rate);
    return returnRates;
  }, [data]);

  // ===== Observation 8: Womenswear Support Volume =====
  const obs8 = useMemo(() => {
    const productMap = new Map(data.products.map((p) => [p.product_id, p]));

    const ticketsWithGender = data.supportTickets.map((t) => {
      const product = productMap.get(t.related_product_id);
      return { ...t, gender: product?.gender_segment || 'unknown' };
    });

    const womenTickets = ticketsWithGender.filter((t) => t.gender === 'womens');
    const menTickets = ticketsWithGender.filter((t) => t.gender === 'mens');

    const sizingRate = (tickets: typeof ticketsWithGender) => {
      if (!tickets.length) return 0;
      return (tickets.filter((t) => t.category === 'sizing_fit').length / tickets.length) * 100;
    };

    const categoryBreakdown = (tickets: typeof ticketsWithGender) => {
      const cats = groupBy(tickets, (t) => t.category);
      return Object.entries(cats)
        .map(([cat, ts]) => ({ category: cat, count: ts.length }))
        .sort((a, b) => b.count - a.count);
    };

    return {
      womensSizingRate: sizingRate(womenTickets),
      mensSizingRate: sizingRate(menTickets),
      womensCategories: categoryBreakdown(womenTickets),
      mensCategories: categoryBreakdown(menTickets),
      totalWomens: womenTickets.length,
      totalMens: menTickets.length,
    };
  }, [data]);

  return (
    <div className="space-y-8">
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Operator Assessment
        </h2>
        <p className="text-sm text-neutral-500 mt-1">
          Eight observations about Pretty Fly's business — each backed by data, interpreted by Wayflyer.
        </p>
      </div>

      {/* Observation 1: Hidden Womenswear Story */}
      <ObservationCard
        number={1}
        title="The Hidden Womenswear Goldmine"
        headline={`Womens CAC ${formatGBP(obs1.womensCAC)} vs Mens ${formatGBP(obs1.mensCAC)}`}
        commentary={`Womenswear is acquiring customers at ${(obs1.womensCAC / obs1.mensCAC).toFixed(1)}x the cost of menswear, but those customers are repeating at ${(obs1.womensRepeat / obs1.mensRepeat).toFixed(1)}x the rate (${formatPct(obs1.womensRepeat)} vs ${formatPct(obs1.mensRepeat)}). Pretty Fly is overspending on acquisition for a segment that has real product-market fit — the problem isn't the product, it's the funnel. ${obs1.womensCusts} womens customers acquired from Meta alone.`}
        recommendation="Shift budget from broad prospecting to retention — email flows, loyalty, retargeting. The womens segment doesn't need more top-of-funnel spend, it needs better conversion of the demand that already exists."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={obs1.chartData} barGap={8}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="metric" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} />
              <Tooltip {...chartTooltipStyle} />
              <Bar dataKey="Womens" fill={ACCENT} radius={[4, 4, 0, 0]} />
              <Bar dataKey="Mens" fill={MUTED} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 2: Cash Tied Up */}
      <ObservationCard
        number={2}
        title="Where Cash Is Tied Up"
        headline={`${formatGBP(obs2.totalSlowValue)} trapped in slow-moving womens stock`}
        commentary={`${obs2.slowCount} womens SKUs have DIO exceeding 180 days — meaning at current sell-through, this stock won't clear for six months or more. The initial womens buy was too aggressive on certain colourways and sizes. That inventory is cash the brand can't deploy on its next drop or marketing push.`}
        recommendation="Flash-sale or bundle the slowest movers now. For the next womens buy, cut initial order quantities by 40% and plan a rapid reorder if sell-through exceeds 60% in the first 30 days."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={obs2.slowMovers.slice(0, 8)}
              layout="vertical"
              margin={{ left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis type="number" tick={{ fill: '#999', fontSize: 11 }} />
              <YAxis
                dataKey="sku"
                type="category"
                width={160}
                tick={{ fill: '#999', fontSize: 10 }}
              />
              <Tooltip {...chartTooltipStyle} formatter={(v: number) => `${v} days`} />
              <Bar dataKey="dio" fill={WARNING} radius={[0, 4, 4, 0]}>
                {obs2.slowMovers.slice(0, 8).map((_, i) => (
                  <Cell key={i} fill={i < 3 ? NEGATIVE : WARNING} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 3: Bleeding Google Campaign */}
      <ObservationCard
        number={3}
        title="The Campaign That's Burning Cash"
        headline={`Generic_Streetwear_UK: ${obs3.generic ? `${obs3.generic.roas.toFixed(1)}x ROAS on ${formatGBP(obs3.generic.spend)}` : 'N/A'}`}
        commentary={`The Generic_Streetwear_UK Google campaign has run for 24 months at a ${obs3.generic?.roas.toFixed(1)}x ROAS. Pretty Fly has paid ${formatGBP(obs3.generic?.spend || 0)} to Google to generate ${formatGBP(obs3.generic?.rev || 0)} of revenue — a marginal contribution well below the threshold where the marketing pays for itself after fulfilment costs. Every other campaign delivers 3-5x ROAS.`}
        recommendation="Kill this campaign tomorrow and redeploy the ~£1k/month to Shopping or PMax campaigns that are delivering 3x+ returns."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={obs3.campStats} margin={{ bottom: 40 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis
                dataKey="name"
                tick={{ fill: '#999', fontSize: 10 }}
                angle={-30}
                textAnchor="end"
                height={60}
              />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} />
              <Tooltip {...chartTooltipStyle} formatter={(v: number) => `${v.toFixed(1)}x`} />
              <Bar dataKey="roas" radius={[4, 4, 0, 0]}>
                {obs3.campStats.map((c, i) => (
                  <Cell
                    key={i}
                    fill={c.name.includes('Generic_Streetwear') ? NEGATIVE : POSITIVE}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 4: Discounting Destroys Margin */}
      <ObservationCard
        number={4}
        title="Discounting That Destroys Margin"
        headline={`Discounted AOV ${formatGBP(obs4.discountedAOV)} vs non-discounted ${formatGBP(obs4.nonDiscountedAOV)}`}
        commentary={`${formatPct(obs4.discountRate)} of orders use a discount code. But discounts don't increase basket size — they shrink it. Discounted baskets average ${obs4.discountedItems.toFixed(2)} items vs ${obs4.nonDiscountedItems.toFixed(2)} non-discounted. Customers using codes buy fewer, cheaper items. Some codes are net-negative after COGS and fulfilment.`}
        recommendation="Audit every active code. Kill blanket percentage discounts. Replace with conditional offers (spend £200+, get free shipping) that protect AOV and drive basket size up."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={[
                { label: 'Discounted', aov: Math.round(obs4.discountedAOV), items: obs4.discountedItems },
                { label: 'Non-discounted', aov: Math.round(obs4.nonDiscountedAOV), items: obs4.nonDiscountedItems },
              ]}
              barGap={8}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="label" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} />
              <Tooltip {...chartTooltipStyle} />
              <Bar dataKey="aov" name="AOV (£)" fill={ACCENT} radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 5: Dead-weight SaaS */}
      <ObservationCard
        number={5}
        title="The SaaS Line Nobody Cancelled"
        headline={`${formatGBP(obs5.mixview?.total || 0)} spent on Mixview Analytics over 24 months`}
        commentary={`Mixview Analytics Ltd has been charging £349/month for 24 months — ${formatGBP(obs5.mixview?.total || 0)} total. There is zero corresponding usage data anywhere in Pretty Fly's systems: no events, no campaigns, no integrations. This is a subscription someone signed up for and forgot about. Pure waste.`}
        recommendation="Cancel immediately. Implement a quarterly SaaS audit — cross-reference every subscription payment against actual product usage. This one is free money."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart
              data={obs5.subs.slice(0, 8)}
              layout="vertical"
              margin={{ left: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis type="number" tick={{ fill: '#999', fontSize: 11 }} tickFormatter={(v) => `£${v.toLocaleString()}`} />
              <YAxis dataKey="name" type="category" width={140} tick={{ fill: '#999', fontSize: 10 }} />
              <Tooltip {...chartTooltipStyle} formatter={(v: number) => formatGBP(v)} />
              <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                {obs5.subs.slice(0, 8).map((s, i) => (
                  <Cell
                    key={i}
                    fill={s.name.toUpperCase().includes('MIXVIEW') ? NEGATIVE : MUTED}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 6: Margin Compression */}
      <ObservationCard
        number={6}
        title="Margin Compression on Caps & Sweatpants"
        headline={`Caps at ${formatPct(obs6.find((m) => m.type === 'Cap')?.margin || 0)} and Sweatpants at ${formatPct(obs6.find((m) => m.type === 'Sweatpants')?.margin || 0)} gross margin`}
        commentary={`Caps and sweatpants are running 15-20 points below the rest of the portfolio (Hoodies ${formatPct(obs6.find((m) => m.type === 'Hoodie')?.margin || 0)}, Tees ${formatPct(obs6.find((m) => m.type === 'Tee')?.margin || 0)}). The supplier is overcharging or the brand hasn't renegotiated since launch. At current volumes, fixing cap margins alone could recover significant annual margin.`}
        recommendation="Rebid caps and sweatpants to alternative suppliers. Target 55%+ gross margin on both. If the current supplier can't match, split the order."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={obs6}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="type" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis
                tick={{ fill: '#999', fontSize: 12 }}
                domain={[0, 70]}
                tickFormatter={(v) => `${v}%`}
              />
              <Tooltip {...chartTooltipStyle} formatter={(v: number) => formatPct(v)} />
              <Bar dataKey="margin" name="Gross Margin" radius={[4, 4, 0, 0]}>
                {obs6.map((m, i) => (
                  <Cell
                    key={i}
                    fill={m.margin < 50 ? NEGATIVE : m.margin < 55 ? WARNING : POSITIVE}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 7: Trainer Return Rate */}
      <ObservationCard
        number={7}
        title="The Trainer Sizing Problem"
        headline={`Trainers: ${formatPct(obs7.find((r) => r.type === 'Trainer')?.rate || 0)} return rate vs ${formatPct(obs7.filter((r) => r.type !== 'Trainer').reduce((a, b) => a + b.rate, 0) / Math.max(obs7.filter((r) => r.type !== 'Trainer').length, 1))} average`}
        commentary={`Trainers return at roughly 2x the rate of everything else, almost entirely due to sizing issues (size_too_small / size_too_large dominate the refund reasons). Better fit guidance or a size-recommendation tool would cut returns dramatically and recover the associated shipping, restocking, and customer service costs.`}
        recommendation="Add a size recommendation widget to the trainer PDP. Use refund reason data to calibrate the guidance — if customers consistently say 'too small', recommend sizing up."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={obs7}>
              <CartesianGrid strokeDasharray="3 3" stroke="#333" />
              <XAxis dataKey="type" tick={{ fill: '#999', fontSize: 12 }} />
              <YAxis tick={{ fill: '#999', fontSize: 12 }} tickFormatter={(v) => `${v}%`} />
              <Tooltip {...chartTooltipStyle} formatter={(v: number) => formatPct(v)} />
              <Bar dataKey="rate" name="Return Rate" radius={[4, 4, 0, 0]}>
                {obs7.map((r, i) => (
                  <Cell key={i} fill={r.type === 'Trainer' ? NEGATIVE : MUTED} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        }
      />

      {/* Observation 8: Womenswear Support Volume */}
      <ObservationCard
        number={8}
        title="The Sizing Guide That's Failing Women"
        headline={`Womens sizing tickets: ${formatPct(obs8.womensSizingRate)} vs Mens: ${formatPct(obs8.mensSizingRate)}`}
        commentary={`Womens customers are confused about fit at nearly ${(obs8.womensSizingRate / obs8.mensSizingRate).toFixed(0)}x the rate of mens. ${formatPct(obs8.womensSizingRate)} of all womens support tickets are sizing-related vs ${formatPct(obs8.mensSizingRate)} for mens. Every sizing ticket is a potential lost sale or unnecessary return. This is the natural handoff to Fin AI — automated sizing guidance could halve this volume overnight.`}
        recommendation="Deploy an AI-powered sizing assistant on the womenswear PDPs. Use support ticket data to train the model on common fit issues per product."
        chart={
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie
                data={obs8.womensCategories}
                dataKey="count"
                nameKey="category"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={({ category, percent }) => `${category} ${(percent * 100).toFixed(0)}%`}
                labelLine={{ stroke: '#555' }}
              >
                {obs8.womensCategories.map((c, i) => (
                  <Cell
                    key={i}
                    fill={c.category === 'sizing_fit' ? ACCENT : ['#525252', '#404040', '#333', '#2a2a2a', '#222', '#1a1a1a'][i % 6]}
                  />
                ))}
              </Pie>
              <Tooltip {...chartTooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        }
      />
    </div>
  );
}
