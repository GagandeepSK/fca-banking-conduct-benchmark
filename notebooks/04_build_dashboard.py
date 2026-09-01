"""Build interactive HTML dashboard — finance-framed version with cost model and Consumer Duty."""

import pandas as pd, json, math
from pathlib import Path

ROOT    = Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark")
OUTPUTS = ROOT / "data" / "outputs"

def clean_nan(obj):
    if isinstance(obj, float) and math.isnan(obj): return None
    if isinstance(obj, dict): return {k: clean_nan(v) for k,v in obj.items()}
    if isinstance(obj, list): return [clean_nan(i) for i in obj]
    return obj

def fmt_gbp(v):
    if v is None: return "N/A"
    if v >= 1e9:  return f"£{v/1e9:.2f}bn"
    if v >= 1e6:  return f"£{v/1e6:.1f}m"
    return f"£{v/1e3:.0f}k"

market      = pd.read_csv(OUTPUTS / "kpi_volume_by_period.csv")
prod        = pd.read_csv(OUTPUTS / "kpi_volume_by_product.csv")
bench       = pd.read_csv(OUTPUTS / "kpi_firm_benchmark.csv")
uphold_p    = pd.read_csv(OUTPUTS / "kpi_uphold_by_product.csv")
closure     = pd.read_csv(OUTPUTS / "kpi_closure_performance.csv")
opp         = pd.read_csv(OUTPUTS / "kpi_opportunities.csv")
scen        = pd.read_csv(OUTPUTS / "kpi_scenarios.csv")
cost_firms  = pd.read_csv(OUTPUTS / "kpi_cost_model_firms.csv")
cost_prods  = pd.read_csv(OUTPUTS / "kpi_cost_by_product.csv")

PERIODS  = ["2024H1","2024H2","2025H1","2025H2"]
PRODUCTS = ["Banking and credit cards","Decumulation & pensions","Home finance",
            "Insurance & pure protection","Investments"]
PROD_COL = ["#2563eb","#7c3aed","#059669","#dc2626","#d97706"]

market_totals = {r["reporting_period"]: int(r["market_complaints"]) for _,r in market.iterrows()}

prod_by_period = {}
for p in PERIODS:
    sub = prod[prod["reporting_period"]==p]
    prod_by_period[p] = {row["product_group"]: int(row["total_complaints"])
                         for _,row in sub.iterrows() if pd.notna(row["total_complaints"])}

uphold_by_product = {}
for p in PERIODS:
    sub = uphold_p[uphold_p["reporting_period"]==p]
    uphold_by_product[p] = {row["product_group"]: round(float(row["uphold_rate_weighted_pct"]),1)
                             for _,row in sub.iterrows() if pd.notna(row["uphold_rate_weighted_pct"])}

closure_agg = (closure.groupby(["reporting_period","product_group"])
               .agg(pct_3days=("pct_closed_3days","mean"),
                    pct_8weeks=("pct_closed_3to8weeks","mean"))
               .reset_index())
closure_by_product = {}
for p in PERIODS:
    sub = closure_agg[closure_agg["reporting_period"]==p]
    closure_by_product[p] = {}
    for _,row in sub.iterrows():
        if pd.notna(row["pct_3days"]):
            closure_by_product[p][row["product_group"]] = {
                "pct_3days":  round(float(row["pct_3days"])*100,1),
                "pct_8weeks": round(float(row["pct_8weeks"])*100,1) if pd.notna(row["pct_8weeks"]) else None,
            }

top30 = (bench[bench["reporting_period"]=="2025H2"]
         .nlargest(30,"complaints_opened")["firm_name"].tolist())

# Firm cost lookup
cost_lookup = {row["firm_name"]: int(row["cost_total"]) for _,row in cost_firms.iterrows()}

firm_data = {}
for firm in top30:
    sub = bench[bench["firm_name"]==firm].sort_values("reporting_period")
    firm_data[firm] = {}
    for _,row in sub.iterrows():
        firm_data[firm][row["reporting_period"]] = {
            "vol":  int(row["complaints_opened"])        if pd.notna(row["complaints_opened"]) else None,
            "uph":  round(float(row["uphold_rate_weighted_pct"]),1) if pd.notna(row["uphold_rate_weighted_pct"]) else None,
            "cl3":  round(float(row["pct_3days_mean"])*100,1)       if pd.notna(row["pct_3days_mean"]) else None,
            "rank": int(row["rank_by_volume"])            if pd.notna(row["rank_by_volume"]) else None,
            "cost": cost_lookup.get(firm) if row["reporting_period"]=="2025H2" else None,
        }

top20 = (bench[bench["reporting_period"]=="2025H2"]
         .dropna(subset=["complaints_opened"])
         .nlargest(20,"complaints_opened")
         [["firm_name","complaints_opened","uphold_rate_weighted_pct","rank_by_volume"]])
top20 = top20.merge(cost_firms[["firm_name","cost_total"]], on="firm_name", how="left")
top20_json = clean_nan(top20.to_dict("records"))

prod_2025h2 = prod[prod["reporting_period"]=="2025H2"].copy()
total_vol = prod_2025h2["total_complaints"].sum()
prod_2025h2["share_pct"] = (prod_2025h2["total_complaints"]/total_vol*100).round(1)
prod_2025h2 = prod_2025h2.merge(cost_prods[["product_group","cost_total","uphold_rate_pct"]], on="product_group", how="left")

prod_table = []
for _,row in prod_2025h2.iterrows():
    pg = row["product_group"]
    u  = uphold_by_product.get("2025H2",{}).get(pg)
    c  = closure_by_product.get("2025H2",{}).get(pg,{}).get("pct_3days")
    prod_table.append({
        "pg": pg, "vol": int(row["total_complaints"]) if pd.notna(row["total_complaints"]) else None,
        "share": float(row["share_pct"]), "uphold": u, "cl3": c,
        "cost": int(row["cost_total"]) if pd.notna(row["cost_total"]) else None,
    })

# Enhanced opportunity data with cost
opp_enhanced = opp.merge(cost_prods[["product_group","cost_total","cost_per_compl"]], on="product_group", how="left")
opp_json  = clean_nan(opp_enhanced.fillna("").to_dict("records"))
scen_json = clean_nan(scen.fillna("").to_dict("records"))

market_cost_total = int(cost_firms["cost_total"].sum())

# Scenario with £ impact
vol_2025h2 = market_totals["2025H2"]
avg_cost_per_compl = market_cost_total / vol_2025h2
cost_scenarios = []
for pct in [5,10,15,20]:
    avoided = int(vol_2025h2 * pct/100)
    saving  = int(avoided * avg_cost_per_compl)
    cost_scenarios.append({
        "scenario": f"{pct}% complaint volume reduction",
        "complaints_avoided": avoided,
        "estimated_saving_gbp": saving,
        "assumption": f"Each avoided complaint saves ~£{int(avg_cost_per_compl)} (handling + FOS risk + redress). Modelled, not audited.",
    })

DATA = {
    "periods": PERIODS, "products": PRODUCTS, "prod_col": PROD_COL,
    "market": market_totals,
    "market_cost_total": market_cost_total,
    "avg_cost_per_compl": int(avg_cost_per_compl),
    "prod_by_period": prod_by_period,
    "uphold_by_product": uphold_by_product,
    "closure_by_product": closure_by_product,
    "top30": top30, "firm_data": firm_data, "top20": top20_json,
    "prod_table": prod_table,
    "opp": opp_json, "scen": scen_json,
    "cost_scenarios": cost_scenarios,
}
DATA = clean_nan(DATA)
DATA_JS = "const DATA = " + json.dumps(DATA, indent=2) + ";"

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UK Retail Banking Complaints Benchmark</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js"></script>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#f0f4f8;color:#1e293b;font-size:14px}
header{background:#1e3a5f;color:#fff;padding:14px 28px;display:flex;align-items:center;justify-content:space-between}
header h1{font-size:17px;font-weight:700}
header span{font-size:11px;opacity:.75}
.cd-banner{background:#fef9c3;border-bottom:1px solid #fde047;padding:8px 28px;font-size:12px;color:#713f12}
.cd-banner strong{color:#92400e}
nav{display:flex;background:#fff;border-bottom:2px solid #e2e8f0;padding:0 28px;gap:4px}
.tab{padding:11px 18px;cursor:pointer;font-weight:600;font-size:13px;color:#64748b;border-bottom:3px solid transparent;transition:.15s}
.tab.active{color:#1e3a5f;border-color:#2563eb}
.tab:hover:not(.active){color:#334155}
main{padding:20px 28px;max-width:1400px}
.section{display:none}.section.active{display:block}
.grid{display:grid;gap:16px}
.g2{grid-template-columns:1fr 1fr}.g3{grid-template-columns:1fr 1fr 1fr}.g4{grid-template-columns:repeat(4,1fr)}
.card{background:#fff;border-radius:10px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08)}
.card h3{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.6px;margin-bottom:12px}
.kpi-val{font-size:26px;font-weight:700;color:#1e3a5f;line-height:1}
.kpi-sub{font-size:12px;color:#94a3b8;margin-top:5px}
.kpi-cost{font-size:13px;font-weight:600;color:#7c3aed;margin-top:4px}
.delta{display:inline-block;margin-top:6px;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}
.up{background:#fef2f2;color:#dc2626}.dn{background:#f0fdf4;color:#16a34a}.neu{background:#f1f5f9;color:#475569}
.chart-wrap{position:relative;height:260px}.chart-wrap.tall{height:320px}
select{padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px;background:#fff}
label{font-size:11px;font-weight:700;color:#475569;display:block;margin-bottom:5px;text-transform:uppercase;letter-spacing:.4px}
table{width:100%;border-collapse:collapse;font-size:13px}
thead tr{background:#f8fafc}
th{padding:8px 10px;text-align:left;font-weight:700;color:#475569;border-bottom:2px solid #e2e8f0;white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid #f1f5f9}
tr:hover td{background:#f8fafc}
.badge{display:inline-block;padding:2px 7px;border-radius:9px;font-size:11px;font-weight:700}
.br{background:#fef2f2;color:#dc2626}.ba{background:#fffbeb;color:#d97706}.bg{background:#f0fdf4;color:#16a34a}
.src{font-size:11px;color:#94a3b8;margin-top:8px;font-style:italic}
.opp{padding:14px 16px;border-left:4px solid #2563eb;background:#f8fafc;border-radius:0 8px 8px 0;margin-bottom:10px}
.opp h4{font-size:13px;font-weight:700;margin-bottom:6px}
.opp-meta{display:flex;gap:14px;flex-wrap:wrap}
.om{font-size:12px;color:#64748b}.om strong{color:#1e293b}
.om.cost strong{color:#7c3aed}
.scard{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:10px}
.scard h4{font-size:13px;font-weight:700;margin-bottom:4px}
.scard p{font-size:12px;color:#64748b;margin-bottom:10px;font-style:italic}
.sg{display:flex;gap:10px;flex-wrap:wrap}
.sv{text-align:center;padding:8px 14px;background:#fff;border-radius:6px;border:1px solid #e2e8f0;min-width:110px}
.sv .n{font-size:15px;font-weight:700;color:#1e3a5f}.sv.purple .n{color:#7c3aed}
.sv .l{font-size:11px;color:#64748b;margin-top:2px}
.cd-note{background:#fef9c3;border:1px solid #fde047;border-radius:8px;padding:12px 16px;font-size:12px;color:#713f12;margin-bottom:16px}
.cd-note strong{color:#92400e}
@media(max-width:900px){.g4{grid-template-columns:1fr 1fr}.g2{grid-template-columns:1fr}.g3{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <h1>UK Retail Banking Complaints Benchmark</h1>
  <span>FCA Firm-Level Data &nbsp;|&nbsp; 2024H1 – 2025H2 &nbsp;|&nbsp; ~220 Firms Per Period</span>
</header>
<div class="cd-banner">
  <strong>Consumer Duty context:</strong> Under FCA Consumer Duty (effective July 2023), firms must demonstrate good outcomes for retail customers. Uphold rates and complaint volumes are direct evidence the FCA uses to assess whether firms are meeting the Duty. High uphold rates signal systematic product or process failure, not just poor complaint handling.
</div>
<nav>
  <div class="tab active" onclick="showTab('overview')">Executive Overview</div>
  <div class="tab" onclick="showTab('firm')">Firm Benchmark</div>
  <div class="tab" onclick="showTab('product')">Product Benchmark</div>
  <div class="tab" onclick="showTab('priority')">Risk &amp; Cost Exposure</div>
</nav>
<main>

<!-- OVERVIEW -->
<div id="overview" class="section active">
  <div class="grid g4" style="margin-bottom:16px">
    <div class="card"><h3>Complaints Opened (2025H2)</h3><div class="kpi-val" id="k-vol"></div><div class="kpi-sub">All firms, all products</div><div class="delta" id="k-vol-d"></div></div>
    <div class="card"><h3>Est. Industry Cost Exposure</h3><div class="kpi-val" id="k-cost"></div><div class="kpi-cost">Per 6-month period (modelled)</div><div class="kpi-sub">Handling + FOS risk + redress</div></div>
    <div class="card"><h3>Largest Product (2025H2)</h3><div class="kpi-val" id="k-top-prod"></div><div class="kpi-sub" id="k-top-share"></div></div>
    <div class="card"><h3>Market Trend (2024H1–2025H2)</h3><div class="kpi-val" id="k-trend"></div><div class="kpi-sub">Total complaints change over 4 periods</div></div>
  </div>
  <div class="grid g2" style="margin-bottom:16px">
    <div class="card">
      <h3>Market Complaint Volume by Period</h3>
      <div class="chart-wrap"><canvas id="c-market"></canvas></div>
      <p class="src">FCA complaints opened per 6-month period across ~220 qualifying firms.</p>
    </div>
    <div class="card">
      <h3>Product Mix — 2025H2</h3>
      <div class="chart-wrap"><canvas id="c-prodmix"></canvas></div>
    </div>
  </div>
  <div class="grid g2">
    <div class="card">
      <h3>Top 20 Firms by Complaint Volume — 2025H2</h3>
      <div class="chart-wrap tall"><canvas id="c-topfirms"></canvas></div>
    </div>
    <div class="card">
      <h3>Top 20 Firms — Volume, Uphold Rate &amp; Cost Exposure</h3>
      <div style="overflow-y:auto;max-height:340px">
      <table><thead><tr><th>#</th><th>Firm</th><th>Complaints</th><th>Uphold %</th><th>Est. Cost</th></tr></thead>
      <tbody id="t-top20"></tbody></table>
      </div>
      <p class="src">Cost = handling (£200/complaint) + FOS risk (8% × £650) + redress (uphold rate × £300). Assumptions stated — not audited figures.</p>
    </div>
  </div>
</div>

<!-- FIRM BENCHMARK -->
<div id="firm" class="section">
  <div style="margin-bottom:16px;display:flex;align-items:flex-end;gap:24px">
    <div><label>Select Firm</label><select id="firm-sel" onchange="updateFirm()"></select></div>
    <div class="kpi-sub">Top 30 firms by 2025H2 complaint volume</div>
  </div>
  <div class="grid g4" style="margin-bottom:16px">
    <div class="card"><h3>Complaints (2025H2)</h3><div class="kpi-val" id="fb-v"></div><div class="delta" id="fb-vd"></div></div>
    <div class="card"><h3>Uphold Rate % (2025H2)</h3><div class="kpi-val" id="fb-u"></div><div class="kpi-sub">Weighted by complaints — Consumer Duty signal</div></div>
    <div class="card"><h3>% Closed Within 3 Days</h3><div class="kpi-val" id="fb-c"></div><div class="kpi-sub">FCA closure timing metric</div></div>
    <div class="card"><h3>Est. Cost Exposure (2025H2)</h3><div class="kpi-val" id="fb-cost"></div><div class="kpi-sub">Modelled — see assumptions</div></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>Complaint Volume — All Periods</h3><div class="chart-wrap"><canvas id="c-firm-vol"></canvas></div></div>
    <div class="card"><h3>Uphold Rate % — All Periods (Consumer Duty indicator)</h3><div class="chart-wrap"><canvas id="c-firm-uph"></canvas></div></div>
  </div>
</div>

<!-- PRODUCT BENCHMARK -->
<div id="product" class="section">
  <div class="grid g2" style="margin-bottom:16px">
    <div class="card"><h3>Complaint Volume by Product — All Periods</h3><div class="chart-wrap tall"><canvas id="c-pvol"></canvas></div></div>
    <div class="card"><h3>Uphold Rate % by Product — All Periods</h3><div class="chart-wrap tall"><canvas id="c-puph"></canvas></div></div>
  </div>
  <div class="grid g2">
    <div class="card"><h3>% Closed Within 3 Days by Product</h3><div class="chart-wrap"><canvas id="c-pcl"></canvas></div></div>
    <div class="card">
      <h3>Product Summary — 2025H2 with Cost Exposure</h3>
      <table><thead><tr><th>Product</th><th>Complaints</th><th>Share %</th><th>Uphold %</th><th>3-Day %</th><th>Est. Cost</th></tr></thead>
      <tbody id="t-prod"></tbody></table>
      <p class="src">Uphold rate weighted by volume. Cost = modelled estimate per assumptions. High uphold on Decumulation & pensions (70%) is a direct Consumer Duty concern.</p>
    </div>
  </div>
</div>

<!-- RISK & COST EXPOSURE -->
<div id="priority" class="section">
  <div class="cd-note">
    <strong>Consumer Duty framing:</strong> The FCA's Consumer Duty (PS22/9) requires firms to deliver good outcomes across four areas: products &amp; services, price &amp; value, consumer understanding, and consumer support. Complaint uphold rates are a primary FCA supervisory metric. A sustained uphold rate above 50% in any product area indicates systematic failure to deliver the Duty — not merely a complaint-handling issue.
  </div>
  <div class="grid g2" style="margin-bottom:16px">
    <div class="card">
      <h3>Risk Matrix — Volume vs Uphold Rate (2025H2)</h3>
      <div class="chart-wrap tall"><canvas id="c-scatter"></canvas></div>
      <p class="src">Bubble size = estimated cost exposure. X axis = uphold rate (FCA's primary Consumer Duty signal). Upper-right quadrant = highest regulatory and cost risk.</p>
    </div>
    <div class="card">
      <h3>Ranked Risk &amp; Cost Areas</h3>
      <div id="opp-list"></div>
    </div>
  </div>
  <div class="card">
    <h3>Scenario Modelling — £ Impact of Operational Improvement</h3>
    <p class="src" style="margin-bottom:12px">Assumption: avg cost per complaint ≈ £<span id="avg-cost"></span> (handling + FOS risk + redress). Scenarios are modelled estimates, not forecasts. All assumptions are stated.</p>
    <div id="scen-list"></div>
  </div>
</div>

</main>
<script>
%%DATA_JS%%

const fmt  = n => n==null ? "N/A" : Number(n).toLocaleString();
const fmtP = n => n==null ? "N/A" : n.toFixed(1)+"%";
const fmtG = n => {
  if(n==null) return "N/A";
  if(n>=1e9)  return "£"+(n/1e9).toFixed(2)+"bn";
  if(n>=1e6)  return "£"+(n/1e6).toFixed(1)+"m";
  return "£"+(n/1e3).toFixed(0)+"k";
};
const PERIODS = DATA.periods;
let charts = {};
function destroyChart(id){ if(charts[id]){charts[id].destroy();delete charts[id];} }

function showTab(t){
  document.querySelectorAll(".section").forEach(s=>s.classList.remove("active"));
  document.querySelectorAll(".tab").forEach(s=>s.classList.remove("active"));
  document.getElementById(t).classList.add("active");
  document.querySelectorAll(".tab").forEach(el=>{
    if(el.getAttribute("onclick").includes("'"+t+"'")) el.classList.add("active");
  });
  if(t==="firm")    initFirmTab();
  if(t==="product") initProductTab();
  if(t==="priority") initPriorityTab();
}

function initOverview(){
  const m=DATA.market, v2=m["2025H2"], v1=m["2025H1"], v0=m["2024H1"];
  document.getElementById("k-vol").textContent=fmt(v2);
  document.getElementById("k-cost").textContent=fmtG(DATA.market_cost_total);
  const chg=((v2-v1)/v1*100).toFixed(1);
  const dd=document.getElementById("k-vol-d");
  dd.textContent=(chg>=0?"+":"")+chg+"% vs 2025H1"; dd.className="delta "+(chg>=0?"up":"dn");
  const pm=DATA.prod_by_period["2025H2"];
  const top=Object.entries(pm).sort((a,b)=>b[1]-a[1])[0];
  document.getElementById("k-top-prod").textContent="Banking & CC";
  document.getElementById("k-top-share").textContent=fmt(top[1])+" complaints ("+(top[1]/v2*100).toFixed(1)+"%)";
  const tc=((v2-v0)/v0*100).toFixed(1);
  document.getElementById("k-trend").textContent=(tc>=0?"+":"")+tc+"%";

  destroyChart("c-market");
  charts["c-market"]=new Chart(document.getElementById("c-market"),{type:"bar",
    data:{labels:PERIODS,datasets:[{label:"Complaints",data:PERIODS.map(p=>m[p]),
      backgroundColor:PERIODS.map((_,i)=>i===3?"#2563eb":"#93c5fd"),borderRadius:4}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>" "+fmt(c.raw)}}},
      scales:{y:{ticks:{callback:v=>fmt(v)},grid:{color:"#f1f5f9"}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});

  const pm2=DATA.prod_by_period["2025H2"];
  destroyChart("c-prodmix");
  charts["c-prodmix"]=new Chart(document.getElementById("c-prodmix"),{type:"doughnut",
    data:{labels:DATA.products,datasets:[{data:DATA.products.map(p=>pm2[p]||0),
      backgroundColor:DATA.prod_col,borderWidth:2}]},
    options:{plugins:{legend:{position:"right",labels:{font:{size:11},boxWidth:14}},
      tooltip:{callbacks:{label:c=>" "+fmt(c.raw)+" ("+(c.raw/v2*100).toFixed(1)+"%)"}}}},
      responsive:true,maintainAspectRatio:false}});

  const t20=DATA.top20;
  destroyChart("c-topfirms");
  charts["c-topfirms"]=new Chart(document.getElementById("c-topfirms"),{type:"bar",
    data:{labels:t20.map(f=>{const n=f.firm_name;return n.length>28?n.slice(0,26)+"…":n;}),
      datasets:[{label:"Complaints",data:t20.map(f=>f.complaints_opened),backgroundColor:"#2563eb",borderRadius:3}]},
    options:{indexAxis:"y",plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>" "+fmt(c.raw)}}},
      scales:{x:{ticks:{callback:v=>fmt(v)},grid:{color:"#f1f5f9"}},y:{ticks:{font:{size:10}},grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});

  const tbody=document.getElementById("t-top20");
  tbody.innerHTML=t20.map((f,i)=>{
    const u=f.uphold_rate_weighted_pct;
    const ub=u==null?"":u>60?`<span class="badge br">${u.toFixed(1)}%</span>`:u>45?`<span class="badge ba">${u.toFixed(1)}%</span>`:`<span class="badge bg">${u.toFixed(1)}%</span>`;
    return `<tr><td>${i+1}</td><td>${f.firm_name}</td><td>${fmt(f.complaints_opened)}</td><td>${ub}</td><td style="color:#7c3aed;font-weight:600">${fmtG(f.cost_total)}</td></tr>`;
  }).join("");
}

function initFirmTab(){
  const sel=document.getElementById("firm-sel");
  if(!sel.options.length) DATA.top30.forEach(f=>{const o=document.createElement("option");o.value=f;o.text=f;sel.appendChild(o);});
  updateFirm();
}

function updateFirm(){
  const firm=document.getElementById("firm-sel").value;
  const fd=DATA.firm_data[firm];
  const d2=fd["2025H2"]||{}, d1=fd["2025H1"]||{};
  document.getElementById("fb-v").textContent=d2.vol!=null?fmt(d2.vol):"N/A";
  document.getElementById("fb-u").textContent=d2.uph!=null?d2.uph.toFixed(1)+"%":"N/A";
  document.getElementById("fb-c").textContent=d2.cl3!=null?d2.cl3.toFixed(1)+"%":"N/A";
  document.getElementById("fb-cost").textContent=d2.cost!=null?fmtG(d2.cost):"N/A";
  if(d2.vol!=null&&d1.vol!=null){
    const chg=((d2.vol-d1.vol)/d1.vol*100).toFixed(1);
    const el=document.getElementById("fb-vd");
    el.textContent=(chg>=0?"+":"")+chg+"% vs 2025H1"; el.className="delta "+(chg>=0?"up":"dn");
  } else document.getElementById("fb-vd").textContent="";

  destroyChart("c-firm-vol");
  charts["c-firm-vol"]=new Chart(document.getElementById("c-firm-vol"),{type:"line",
    data:{labels:PERIODS,datasets:[{label:"Complaints",data:PERIODS.map(p=>fd[p]?fd[p].vol:null),
      borderColor:"#2563eb",backgroundColor:"rgba(37,99,235,.1)",fill:true,tension:.3,pointRadius:5,spanGaps:false}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>" "+fmt(c.raw)}}},
      scales:{y:{ticks:{callback:v=>fmt(v)},grid:{color:"#f1f5f9"}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});

  destroyChart("c-firm-uph");
  charts["c-firm-uph"]=new Chart(document.getElementById("c-firm-uph"),{type:"line",
    data:{labels:PERIODS,datasets:[{label:"Uphold %",data:PERIODS.map(p=>fd[p]?fd[p].uph:null),
      borderColor:"#dc2626",backgroundColor:"rgba(220,38,38,.08)",fill:true,tension:.3,pointRadius:5,spanGaps:false}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>c.raw!=null?c.raw.toFixed(1)+"%":"N/A"}}},
      scales:{y:{min:0,max:100,ticks:{callback:v=>v+"%"},grid:{color:"#f1f5f9"}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});
}

function initProductTab(){
  const PRODS=DATA.products, PCOL=DATA.prod_col;
  destroyChart("c-pvol");
  charts["c-pvol"]=new Chart(document.getElementById("c-pvol"),{type:"bar",
    data:{labels:PERIODS,datasets:PRODS.map((p,i)=>({label:p,
      data:PERIODS.map(per=>DATA.prod_by_period[per]?DATA.prod_by_period[per][p]:null),
      backgroundColor:PCOL[i],borderRadius:3}))},
    options:{plugins:{legend:{position:"top",labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:c=>" "+fmt(c.raw)}}},
      scales:{x:{grid:{display:false}},y:{ticks:{callback:v=>fmt(v)},grid:{color:"#f1f5f9"}}},
      responsive:true,maintainAspectRatio:false}});

  destroyChart("c-puph");
  charts["c-puph"]=new Chart(document.getElementById("c-puph"),{type:"line",
    data:{labels:PERIODS,datasets:PRODS.map((p,i)=>({label:p,
      data:PERIODS.map(per=>DATA.uphold_by_product[per]?DATA.uphold_by_product[per][p]:null),
      borderColor:PCOL[i],backgroundColor:"transparent",tension:.3,pointRadius:4,spanGaps:false}))},
    options:{plugins:{legend:{position:"top",labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:c=>c.raw!=null?c.raw.toFixed(1)+"%":"N/A"}}},
      scales:{y:{min:0,max:100,ticks:{callback:v=>v+"%"},grid:{color:"#f1f5f9"}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});

  destroyChart("c-pcl");
  charts["c-pcl"]=new Chart(document.getElementById("c-pcl"),{type:"bar",
    data:{labels:PERIODS,datasets:PRODS.map((p,i)=>({label:p,
      data:PERIODS.map(per=>{const c=DATA.closure_by_product[per];return c&&c[p]?c[p].pct_3days:null;}),
      backgroundColor:PCOL[i],borderRadius:3}))},
    options:{plugins:{legend:{position:"top",labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:c=>c.raw!=null?c.raw.toFixed(1)+"%":"N/A"}}},
      scales:{x:{grid:{display:false}},y:{min:0,max:100,ticks:{callback:v=>v+"%"},grid:{color:"#f1f5f9"}}},
      responsive:true,maintainAspectRatio:false}});

  const tb=document.getElementById("t-prod");
  tb.innerHTML=DATA.prod_table.map(r=>{
    const ub=r.uphold==null?"N/A":r.uphold>55?`<span class="badge br">${r.uphold}%</span>`:r.uphold>40?`<span class="badge ba">${r.uphold}%</span>`:`<span class="badge bg">${r.uphold}%</span>`;
    const cb=r.cl3==null?"N/A":r.cl3<25?`<span class="badge br">${r.cl3}%</span>`:r.cl3<40?`<span class="badge ba">${r.cl3}%</span>`:`<span class="badge bg">${r.cl3}%</span>`;
    return `<tr><td>${r.pg}</td><td>${fmt(r.vol)}</td><td>${r.share}%</td><td>${ub}</td><td>${cb}</td><td style="color:#7c3aed;font-weight:600">${fmtG(r.cost)}</td></tr>`;
  }).join("");
}

function initPriorityTab(){
  const opps=DATA.opp;
  document.getElementById("avg-cost").textContent=fmt(DATA.avg_cost_per_compl);
  destroyChart("c-scatter");
  charts["c-scatter"]=new Chart(document.getElementById("c-scatter"),{type:"bubble",
    data:{datasets:[{label:"Product groups",
      data:opps.map(o=>({x:o.avg_uphold_rate_pct||0,y:o.latest_volume||0,
        r:Math.max(8,(o.cost_total||0)/6e6),label:o.product_group})),
      backgroundColor:DATA.prod_col.map(c=>c+"cc"),borderColor:DATA.prod_col,borderWidth:2}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>{
      const d=c.raw;return[d.label,"Volume: "+fmt(d.y),"Uphold: "+d.x+"%","Est. cost: "+fmtG((d.r/8*6e6))];
    }}}},
    scales:{x:{title:{display:true,text:"Avg Uphold Rate % — FCA Consumer Duty signal (higher = more regulatory risk)"},
      min:0,max:100,grid:{color:"#f1f5f9"}},
      y:{title:{display:true,text:"Complaint Volume"},ticks:{callback:v=>fmt(v)},grid:{color:"#f1f5f9"}}},
    responsive:true,maintainAspectRatio:false}});

  const BCOLS=["#dc2626","#d97706","#2563eb","#059669","#7c3aed"];
  document.getElementById("opp-list").innerHTML=opps.map((o,i)=>`
    <div class="opp" style="border-color:${BCOLS[i%5]}">
      <h4>#${o.priority_rank} — ${o.product_group}</h4>
      <div class="opp-meta">
        <div class="om"><strong>${fmt(o.latest_volume)}</strong><br>Complaints</div>
        <div class="om"><strong>${o.avg_uphold_rate_pct!=null?o.avg_uphold_rate_pct+"%":"N/A"}</strong><br>Uphold Rate</div>
        <div class="om"><strong>${o.avg_pct_closed_3days!=null?o.avg_pct_closed_3days+"%":"N/A"}</strong><br>3-Day Closure</div>
        <div class="om cost"><strong>${fmtG(o.cost_total)}</strong><br>Est. Cost (modelled)</div>
      </div>
    </div>`).join("");

  document.getElementById("scen-list").innerHTML=DATA.cost_scenarios.map(s=>`
    <div class="scard">
      <h4>${s.scenario}</h4>
      <p>${s.assumption}</p>
      <div class="sg">
        <div class="sv"><div class="n">${fmt(s.complaints_avoided)}</div><div class="l">Complaints avoided</div></div>
        <div class="sv purple"><div class="n">${fmtG(s.estimated_saving_gbp)}</div><div class="l">Est. cost saving</div></div>
      </div>
    </div>`).join("");
}

initOverview();
</script>
</body>
</html>"""

HTML = HTML.replace("%%DATA_JS%%", DATA_JS)
out = ROOT / "dashboard.html"
out.write_text(HTML, encoding="utf-8")
print(f"Dashboard written: {out.stat().st_size//1024} KB")
