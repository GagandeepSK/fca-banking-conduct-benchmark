"""Build dashboard.html — clean rebuild."""
import pandas as pd, json, math, urllib.request
from pathlib import Path

ROOT    = Path(r"W:\My Documents\Shortcuts & Files\UK Banking Benchmark")
OUTPUTS = ROOT / "data" / "outputs"

def cn(o):
    if isinstance(o, float) and math.isnan(o): return None
    if isinstance(o, dict): return {k:cn(v) for k,v in o.items()}
    if isinstance(o, list): return [cn(i) for i in o]
    return o

market     = pd.read_csv(OUTPUTS/"kpi_volume_by_period.csv")
prod       = pd.read_csv(OUTPUTS/"kpi_volume_by_product.csv")
bench      = pd.read_csv(OUTPUTS/"kpi_firm_benchmark.csv")
uphold_p   = pd.read_csv(OUTPUTS/"kpi_uphold_by_product.csv")
closure    = pd.read_csv(OUTPUTS/"kpi_closure_performance.csv")
cost_firms = pd.read_csv(OUTPUTS/"kpi_cost_model_firms.csv")
cost_prods = pd.read_csv(OUTPUTS/"kpi_cost_by_product.csv")

PERIODS  = ["2024H1","2024H2","2025H1","2025H2"]
PRODUCTS = ["Banking and credit cards","Decumulation & pensions","Home finance",
            "Insurance & pure protection","Investments"]
PCOL     = ["#2563eb","#7c3aed","#059669","#dc2626","#d97706"]

mkt = {r["reporting_period"]:int(r["market_complaints"]) for _,r in market.iterrows()}

pvp = {}
for p in PERIODS:
    s = prod[prod["reporting_period"]==p]
    pvp[p] = {r["product_group"]:int(r["total_complaints"]) for _,r in s.iterrows() if pd.notna(r["total_complaints"])}

ubp = {}
for p in PERIODS:
    s = uphold_p[uphold_p["reporting_period"]==p]
    ubp[p] = {r["product_group"]:round(float(r["uphold_rate_weighted_pct"]),1)
              for _,r in s.iterrows() if pd.notna(r["uphold_rate_weighted_pct"])}

cl_agg = closure.groupby(["reporting_period","product_group"]).agg(
    cl3=("pct_closed_3days","mean")).reset_index()
clp = {}
for p in PERIODS:
    s = cl_agg[cl_agg["reporting_period"]==p]
    clp[p] = {r["product_group"]:round(float(r["cl3"])*100,1) for _,r in s.iterrows() if pd.notna(r["cl3"])}

t15 = bench[bench["reporting_period"]=="2025H2"].dropna(subset=["complaints_opened"]).nlargest(15,"complaints_opened").copy()
t15 = t15.merge(cost_firms[["firm_name","cost_total"]], on="firm_name", how="left")
top15 = [{"n":r["firm_name"],"v":int(r["complaints_opened"]),
           "u":round(float(r["uphold_rate_weighted_pct"]),1) if pd.notna(r["uphold_rate_weighted_pct"]) else None,
           "c":int(r["cost_total"]) if pd.notna(r["cost_total"]) else None}
          for _,r in t15.iterrows()]

tot = prod[prod["reporting_period"]=="2025H2"]["total_complaints"].sum()
cp  = cost_prods.set_index("product_group")
ptable = [{"pg":r["product_group"],"v":int(r["total_complaints"]),"sh":round(r["total_complaints"]/tot*100,1),
           "u":ubp.get("2025H2",{}).get(r["product_group"]),
           "cl":clp.get("2025H2",{}).get(r["product_group"]),
           "c":int(cp.loc[r["product_group"],"cost_total"]) if r["product_group"] in cp.index else None}
          for _,r in prod[prod["reporting_period"]=="2025H2"].iterrows()]
ptable.sort(key=lambda x: x["v"], reverse=True)

top20f = [r["firm_name"] for _,r in t15.iterrows()]
ftrd = {}
for f in top20f:
    s = bench[bench["firm_name"]==f].sort_values("reporting_period")
    ftrd[f] = {r["reporting_period"]:
               {"v":int(r["complaints_opened"]) if pd.notna(r["complaints_opened"]) else None,
                "u":round(float(r["uphold_rate_weighted_pct"]),1) if pd.notna(r["uphold_rate_weighted_pct"]) else None}
               for _,r in s.iterrows()}

market_cost = int(cost_firms["cost_total"].sum())
avg_cpc     = int(market_cost / mkt["2025H2"])

D = cn({"periods":PERIODS,"products":PRODUCTS,"pcol":PCOL,
        "mkt":mkt,"pvp":pvp,"ubp":ubp,"clp":clp,
        "top15":top15,"ptable":ptable,"ftrd":ftrd,"top20f":top20f,
        "market_cost":market_cost,"avg_cpc":avg_cpc})

DATA_JSON = json.dumps(D)

# Download Chart.js
print("Downloading Chart.js...", end=" ")
req = urllib.request.Request(
    "https://cdn.jsdelivr.net/npm/chart.js@4.4.4/dist/chart.umd.min.js",
    headers={"User-Agent":"Mozilla/5.0"})
chartjs = urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
print(f"{len(chartjs)//1024}KB")

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>UK Retail Banking Complaints Benchmark</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,Segoe UI,sans-serif;background:#f0f4f8;color:#1e293b;font-size:14px}
header{background:#1e3a5f;color:#fff;padding:14px 28px;display:flex;justify-content:space-between;align-items:center}
header h1{font-size:17px;font-weight:700}
header p{font-size:11px;opacity:.7}
.banner{background:#fef9c3;border-bottom:1px solid #fde047;padding:8px 28px;font-size:12px;color:#713f12}
.banner b{color:#92400e}
nav{display:flex;background:#fff;border-bottom:2px solid #e2e8f0;padding:0 28px}
.tab{padding:11px 18px;cursor:pointer;font-weight:600;font-size:13px;color:#64748b;border-bottom:3px solid transparent}
.tab.on{color:#1e3a5f;border-color:#2563eb}
.tab:hover{color:#334155}
main{padding:20px 28px}
.page{display:none}.page.on{display:block}
.row{display:flex;gap:16px;margin-bottom:16px;flex-wrap:wrap}
.card{background:#fff;border-radius:10px;padding:18px 20px;box-shadow:0 1px 3px rgba(0,0,0,.08);flex:1;min-width:200px}
.card h3{font-size:11px;font-weight:700;color:#64748b;text-transform:uppercase;letter-spacing:.5px;margin-bottom:10px}
.big{font-size:26px;font-weight:700;color:#1e3a5f}
.sub{font-size:12px;color:#94a3b8;margin-top:4px}
.cost{font-size:13px;font-weight:600;color:#7c3aed;margin-top:3px}
.pill{display:inline-block;margin-top:6px;padding:2px 8px;border-radius:10px;font-size:12px;font-weight:600}
.red{background:#fef2f2;color:#dc2626}.grn{background:#f0fdf4;color:#16a34a}
.wrap{position:relative;height:260px}
.wrap.tall{height:320px}
select{padding:6px 10px;border:1px solid #cbd5e1;border-radius:6px;font-size:13px}
table{width:100%;border-collapse:collapse;font-size:13px}
th{padding:8px 10px;text-align:left;font-weight:700;color:#475569;border-bottom:2px solid #e2e8f0;background:#f8fafc;white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid #f1f5f9}
tr:hover td{background:#f8fafc}
.b-r{background:#fef2f2;color:#dc2626;padding:2px 7px;border-radius:8px;font-size:11px;font-weight:700}
.b-a{background:#fffbeb;color:#d97706;padding:2px 7px;border-radius:8px;font-size:11px;font-weight:700}
.b-g{background:#f0fdf4;color:#16a34a;padding:2px 7px;border-radius:8px;font-size:11px;font-weight:700}
.note{font-size:11px;color:#94a3b8;margin-top:8px;font-style:italic}
.cd{background:#f8fafc;border:1px solid #e2e8f0;border-left:4px solid #2563eb;border-radius:0 8px 8px 0;padding:14px 16px;margin-bottom:14px}
.cd h4{font-size:13px;font-weight:700;margin-bottom:6px}
.cd p{font-size:12px;color:#475569;line-height:1.6}
.scen{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;margin-bottom:10px}
.scen h4{font-weight:700;margin-bottom:4px}
.scen p{font-size:12px;color:#64748b;font-style:italic;margin-bottom:10px}
.sv{display:inline-block;text-align:center;padding:8px 16px;background:#fff;border:1px solid #e2e8f0;border-radius:6px;margin-right:8px;min-width:120px}
.sv .n{font-size:16px;font-weight:700;color:#1e3a5f}
.sv.p .n{color:#7c3aed}
.sv .l{font-size:11px;color:#64748b;margin-top:2px}
</style>
</head>
<body>
<header>
  <h1>UK Retail Banking Complaints Benchmark</h1>
  <p>FCA Firm-Level Data &nbsp;|&nbsp; 2024H1 to 2025H2 &nbsp;|&nbsp; 220+ Firms</p>
</header>
<div class="banner">
  <b>Consumer Duty:</b> Under FCA Consumer Duty (July 2023), uphold rates are a primary supervisory metric. A sustained uphold rate above 50% indicates systematic product or process failure, not just poor complaint handling.
</div>
<nav>
  <div class="tab on" onclick="go('p1',this)">Executive Overview</div>
  <div class="tab"    onclick="go('p2',this)">Firm Benchmark</div>
  <div class="tab"    onclick="go('p3',this)">Product Benchmark</div>
  <div class="tab"    onclick="go('p4',this)">Risk &amp; Cost Exposure</div>
</nav>
<main>

<div id="p1" class="page on">
  <div class="row">
    <div class="card" style="max-width:280px"><h3>Complaints Opened (2025H2)</h3><div class="big" id="v1"></div><div class="sub">All firms and products</div><span class="pill" id="v1d"></span></div>
    <div class="card" style="max-width:280px"><h3>Est. Industry Cost Exposure</h3><div class="big" id="v2"></div><div class="cost">Per 6-month period (modelled)</div><div class="sub">Handling + FOS risk + redress</div></div>
    <div class="card" style="max-width:280px"><h3>Largest Product (2025H2)</h3><div class="big">Banking &amp; CC</div><div class="sub" id="v3"></div></div>
    <div class="card" style="max-width:280px"><h3>Market Trend</h3><div class="big" id="v4"></div><div class="sub">2024H1 to 2025H2 total change</div></div>
  </div>
  <div class="row">
    <div class="card" style="flex:1"><h3>Market Complaint Volume by Period</h3><div class="wrap"><canvas id="c1"></canvas></div><p class="note">Complaints opened per 6-month FCA reporting period across qualifying firms.</p></div>
    <div class="card" style="flex:1"><h3>Product Mix — 2025H2</h3><div class="wrap"><canvas id="c2"></canvas></div></div>
  </div>
  <div class="row">
    <div class="card" style="flex:1"><h3>Top 15 Firms by Volume — 2025H2</h3><div class="wrap tall"><canvas id="c3"></canvas></div></div>
    <div class="card" style="flex:1"><h3>Top 15 Firms — Detail</h3>
      <div style="overflow-y:auto;max-height:340px">
      <table><thead><tr><th>#</th><th>Firm</th><th>Complaints</th><th>Uphold %</th><th>Est. Cost</th></tr></thead><tbody id="t1"></tbody></table>
      </div>
      <p class="note">Cost = handling (200 GBP) + FOS risk (8% x 650 GBP) + redress (uphold rate x 300 GBP). Modelled, not audited.</p>
    </div>
  </div>
</div>

<div id="p2" class="page">
  <div class="row" style="align-items:flex-end">
    <div><label style="font-size:11px;font-weight:700;color:#475569;display:block;margin-bottom:5px">SELECT FIRM</label>
    <select id="fsel" onchange="drawFirm()"></select></div>
    <div class="sub" style="padding-bottom:8px">Top 15 firms by 2025H2 volume</div>
  </div>
  <div class="row">
    <div class="card" style="max-width:220px"><h3>Complaints (2025H2)</h3><div class="big" id="f1"></div><span class="pill" id="f1d"></span></div>
    <div class="card" style="max-width:220px"><h3>Uphold Rate % (2025H2)</h3><div class="big" id="f2"></div><div class="sub">Consumer Duty signal</div></div>
    <div class="card" style="max-width:220px"><h3>% Closed in 3 Days</h3><div class="big" id="f3"></div><div class="sub">FCA closure metric</div></div>
  </div>
  <div class="row">
    <div class="card" style="flex:1"><h3>Complaint Volume — All Periods</h3><div class="wrap"><canvas id="fvol"></canvas></div></div>
    <div class="card" style="flex:1"><h3>Uphold Rate % — All Periods</h3><div class="wrap"><canvas id="fuph"></canvas></div></div>
  </div>
</div>

<div id="p3" class="page">
  <div class="row">
    <div class="card" style="flex:1"><h3>Complaint Volume by Product — All Periods</h3><div class="wrap tall"><canvas id="c4"></canvas></div></div>
    <div class="card" style="flex:1"><h3>Uphold Rate % by Product — All Periods</h3><div class="wrap tall"><canvas id="c5"></canvas></div></div>
  </div>
  <div class="row">
    <div class="card" style="flex:1"><h3>% Closed Within 3 Days by Product</h3><div class="wrap"><canvas id="c6"></canvas></div></div>
    <div class="card" style="flex:1"><h3>Product Summary — 2025H2</h3>
      <table><thead><tr><th>Product</th><th>Complaints</th><th>Share</th><th>Uphold %</th><th>3-Day %</th><th>Est. Cost</th></tr></thead><tbody id="t2"></tbody></table>
      <p class="note">Uphold weighted by volume. Cost is modelled estimate. High uphold on Decumulation (70%) is a Consumer Duty concern.</p>
    </div>
  </div>
</div>

<div id="p4" class="page">
  <div class="cd">
    <h4>Consumer Duty Framing</h4>
    <p>FCA Consumer Duty (PS22/9) requires firms to deliver good outcomes across four areas: products and services, price and value, consumer understanding, and consumer support. Complaint uphold rates above 50% in any product area signal systematic failure to deliver the Duty. The FCA uses this data in supervisory assessments and firm-specific interventions.</p>
  </div>
  <div class="row">
    <div class="card" style="flex:1"><h3>Risk Matrix — Volume vs Uphold Rate (2025H2)</h3><div class="wrap tall"><canvas id="c7"></canvas></div>
    <p class="note">Bubble size = estimated cost exposure. Upper-right = highest regulatory and financial risk.</p></div>
    <div class="card" style="flex:1"><h3>Product Risk and Cost Summary</h3>
      <table><thead><tr><th>Priority</th><th>Product</th><th>Volume</th><th>Uphold %</th><th>Est. Cost</th><th>Key Risk</th></tr></thead><tbody id="t3"></tbody></table>
    </div>
  </div>
  <div class="card"><h3>Scenario Modelling — GBP Impact of Complaint Reduction</h3>
    <p class="note" style="margin-bottom:14px">Average cost per complaint: approx. <span id="avgc"></span> GBP (handling + FOS risk + redress). All scenarios are modelled estimates based on 2025H2 data. Not forecasts.</p>
    <div id="scens"></div>
  </div>
</div>

</main>
<script>
CHARTJS_PLACEHOLDER
</script>
<script>
var D = DATA_PLACEHOLDER;

function fmtn(n){return n==null?'N/A':Number(n).toLocaleString();}
function fmtp(n){return n==null?'N/A':n.toFixed(1)+'%';}
function fmtg(n){
  if(n==null) return 'N/A';
  if(n>=1e9) return 'GBP '+(n/1e9).toFixed(2)+'bn';
  if(n>=1e6) return 'GBP '+(n/1e6).toFixed(1)+'m';
  return 'GBP '+(n/1e3).toFixed(0)+'k';
}
function badge(v,lo,hi){
  var cls=v>hi?'b-r':v>lo?'b-a':'b-g';
  return '<span class="'+cls+'">'+v.toFixed(1)+'%</span>';
}

var charts={};
function dc(id){if(charts[id]){charts[id].destroy();delete charts[id];}}

function go(id,el){
  document.querySelectorAll('.page').forEach(function(e){e.classList.remove('on');});
  document.querySelectorAll('.tab').forEach(function(e){e.classList.remove('on');});
  document.getElementById(id).classList.add('on');
  el.classList.add('on');
  if(id==='p2') initP2();
  if(id==='p3') initP3();
  if(id==='p4') initP4();
}

window.onload = function(){
  var m=D.mkt;
  var v2=m['2025H2'], v1=m['2025H1'], v0=m['2024H1'];
  document.getElementById('v1').textContent = fmtn(v2);
  document.getElementById('v2').textContent = fmtg(D.market_cost);
  var bvol = D.pvp['2025H2']['Banking and credit cards']||0;
  document.getElementById('v3').textContent = fmtn(bvol)+' complaints ('+(bvol/v2*100).toFixed(1)+'%)';
  var tc = ((v2-v0)/v0*100).toFixed(1);
  document.getElementById('v4').textContent = (tc>=0?'+':'')+tc+'%';
  var chg = ((v2-v1)/v1*100).toFixed(1);
  var pill = document.getElementById('v1d');
  pill.textContent = (chg>=0?'+':'')+chg+'% vs 2025H1';
  pill.className = 'pill '+(chg>=0?'red':'grn');

  // Chart 1 - market bar
  dc('c1');
  charts['c1'] = new Chart(document.getElementById('c1'),{
    type:'bar',
    data:{labels:D.periods,
      datasets:[{data:D.periods.map(function(p){return m[p];}),
        backgroundColor:['#93c5fd','#93c5fd','#93c5fd','#2563eb'],borderRadius:4,label:'Complaints'}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return ' '+fmtn(c.raw);}}}},
      scales:{y:{ticks:{callback:function(v){return fmtn(v);}},grid:{color:'#f1f5f9'}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}
  });

  // Chart 2 - doughnut
  var pm = D.pvp['2025H2'];
  dc('c2');
  charts['c2'] = new Chart(document.getElementById('c2'),{
    type:'doughnut',
    data:{labels:D.products,
      datasets:[{data:D.products.map(function(p){return pm[p]||0;}),
        backgroundColor:D.pcol,borderWidth:2}]},
    options:{plugins:{legend:{position:'right',labels:{font:{size:11},boxWidth:14}},
      tooltip:{callbacks:{label:function(c){return ' '+fmtn(c.raw)+' ('+(c.raw/v2*100).toFixed(1)+'%)';}}}},
      responsive:true,maintainAspectRatio:false}
  });

  // Chart 3 - top15 horizontal bar
  dc('c3');
  charts['c3'] = new Chart(document.getElementById('c3'),{
    type:'bar',
    data:{labels:D.top15.map(function(f){var n=f.n;return n.length>28?n.slice(0,26)+'...':n;}),
      datasets:[{data:D.top15.map(function(f){return f.v;}),backgroundColor:'#2563eb',borderRadius:3,label:'Complaints'}]},
    options:{indexAxis:'y',
      plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return ' '+fmtn(c.raw);}}}},
      scales:{x:{ticks:{callback:function(v){return fmtn(v);}},grid:{color:'#f1f5f9'}},y:{ticks:{font:{size:10}},grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}
  });

  // Table 1
  var tb = document.getElementById('t1');
  tb.innerHTML = D.top15.map(function(f,i){
    var u=f.u; var ub=u==null?'N/A':u>60?'<span class="b-r">'+u.toFixed(1)+'%</span>':u>45?'<span class="b-a">'+u.toFixed(1)+'%</span>':'<span class="b-g">'+u.toFixed(1)+'%</span>';
    return '<tr><td>'+(i+1)+'</td><td>'+f.n+'</td><td>'+fmtn(f.v)+'</td><td>'+ub+'</td><td style="color:#7c3aed;font-weight:600">'+fmtg(f.c)+'</td></tr>';
  }).join('');
};

function initP2(){
  var sel = document.getElementById('fsel');
  if(!sel.options.length){
    D.top20f.forEach(function(f){var o=document.createElement('option');o.value=f;o.text=f;sel.appendChild(o);});
  }
  drawFirm();
}

function drawFirm(){
  var f = document.getElementById('fsel').value;
  var fd = D.ftrd[f];
  var d2 = fd['2025H2']||{}, d1 = fd['2025H1']||{};
  document.getElementById('f1').textContent = d2.v!=null?fmtn(d2.v):'N/A';
  document.getElementById('f2').textContent = d2.u!=null?d2.u.toFixed(1)+'%':'N/A';
  // closure from bench — not in ftrd, just show N/A for now
  document.getElementById('f3').textContent = 'See product tab';
  if(d2.v!=null && d1.v!=null){
    var chg=((d2.v-d1.v)/d1.v*100).toFixed(1);
    var pill=document.getElementById('f1d');
    pill.textContent=(chg>=0?'+':'')+chg+'% vs 2025H1';
    pill.className='pill '+(chg>=0?'red':'grn');
  }
  dc('fvol');
  charts['fvol']=new Chart(document.getElementById('fvol'),{type:'line',
    data:{labels:D.periods,datasets:[{label:'Complaints',data:D.periods.map(function(p){return fd[p]?fd[p].v:null;}),
      borderColor:'#2563eb',backgroundColor:'rgba(37,99,235,.1)',fill:true,tension:.3,pointRadius:5,spanGaps:false}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return ' '+fmtn(c.raw);}}}},
      scales:{y:{ticks:{callback:function(v){return fmtn(v);}},grid:{color:'#f1f5f9'}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});
  dc('fuph');
  charts['fuph']=new Chart(document.getElementById('fuph'),{type:'line',
    data:{labels:D.periods,datasets:[{label:'Uphold %',data:D.periods.map(function(p){return fd[p]?fd[p].u:null;}),
      borderColor:'#dc2626',backgroundColor:'rgba(220,38,38,.08)',fill:true,tension:.3,pointRadius:5,spanGaps:false}]},
    options:{plugins:{legend:{display:false},tooltip:{callbacks:{label:function(c){return c.raw!=null?c.raw.toFixed(1)+'%':'N/A';}}}},
      scales:{y:{min:0,max:100,ticks:{callback:function(v){return v+'%';}},grid:{color:'#f1f5f9'}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});
}

function initP3(){
  dc('c4');
  charts['c4']=new Chart(document.getElementById('c4'),{type:'bar',
    data:{labels:D.periods,datasets:D.products.map(function(p,i){return {label:p,
      data:D.periods.map(function(per){return D.pvp[per]?D.pvp[per][p]:null;}),
      backgroundColor:D.pcol[i],borderRadius:3};})},
    options:{plugins:{legend:{position:'top',labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:function(c){return ' '+fmtn(c.raw);}}}},
      scales:{x:{grid:{display:false}},y:{ticks:{callback:function(v){return fmtn(v);}},grid:{color:'#f1f5f9'}}},
      responsive:true,maintainAspectRatio:false}});
  dc('c5');
  charts['c5']=new Chart(document.getElementById('c5'),{type:'line',
    data:{labels:D.periods,datasets:D.products.map(function(p,i){return {label:p,
      data:D.periods.map(function(per){return D.ubp[per]?D.ubp[per][p]:null;}),
      borderColor:D.pcol[i],backgroundColor:'transparent',tension:.3,pointRadius:4,spanGaps:false};})},
    options:{plugins:{legend:{position:'top',labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:function(c){return c.raw!=null?c.raw.toFixed(1)+'%':'N/A';}}}},
      scales:{y:{min:0,max:100,ticks:{callback:function(v){return v+'%';}},grid:{color:'#f1f5f9'}},x:{grid:{display:false}}},
      responsive:true,maintainAspectRatio:false}});
  dc('c6');
  charts['c6']=new Chart(document.getElementById('c6'),{type:'bar',
    data:{labels:D.periods,datasets:D.products.map(function(p,i){return {label:p,
      data:D.periods.map(function(per){return D.clp[per]?D.clp[per][p]:null;}),
      backgroundColor:D.pcol[i],borderRadius:3};})},
    options:{plugins:{legend:{position:'top',labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:function(c){return c.raw!=null?c.raw.toFixed(1)+'%':'N/A';}}}},
      scales:{x:{grid:{display:false}},y:{min:0,max:100,ticks:{callback:function(v){return v+'%';}},grid:{color:'#f1f5f9'}}},
      responsive:true,maintainAspectRatio:false}});
  var tb=document.getElementById('t2');
  tb.innerHTML=D.ptable.map(function(r){
    var ub=r.u==null?'N/A':r.u>55?'<span class="b-r">'+r.u+'%</span>':r.u>40?'<span class="b-a">'+r.u+'%</span>':'<span class="b-g">'+r.u+'%</span>';
    var cb=r.cl==null?'N/A':r.cl<25?'<span class="b-r">'+r.cl+'%</span>':r.cl<40?'<span class="b-a">'+r.cl+'%</span>':'<span class="b-g">'+r.cl+'%</span>';
    return '<tr><td>'+r.pg+'</td><td>'+fmtn(r.v)+'</td><td>'+r.sh+'%</td><td>'+ub+'</td><td>'+cb+'</td><td style="color:#7c3aed;font-weight:600">'+fmtg(r.c)+'</td></tr>';
  }).join('');
}

function initP4(){
  document.getElementById('avgc').textContent = fmtn(D.avg_cpc);
  dc('c7');
  var bubbles = D.ptable.map(function(r,i){return {x:r.u||0, y:r.v||0, r:Math.max(8,(r.c||0)/5000000), label:r.pg, i:i};});
  charts['c7']=new Chart(document.getElementById('c7'),{type:'bubble',
    data:{datasets:D.ptable.map(function(r,i){return {
      label:r.pg,
      data:[{x:r.u||0,y:r.v||0,r:Math.max(8,(r.c||0)/5000000)}],
      backgroundColor:D.pcol[i]+'bb',borderColor:D.pcol[i],borderWidth:2};})},
    options:{plugins:{legend:{position:'bottom',labels:{font:{size:10},boxWidth:12}},
      tooltip:{callbacks:{label:function(c){var d=c.raw;return [c.dataset.label,'Vol: '+fmtn(d.y),'Uphold: '+d.x+'%'];}}}},
      scales:{
        x:{title:{display:true,text:'Uphold Rate % (FCA Consumer Duty signal)'},min:0,max:100,grid:{color:'#f1f5f9'}},
        y:{title:{display:true,text:'Complaint Volume'},ticks:{callback:function(v){return fmtn(v);}},grid:{color:'#f1f5f9'}}},
      responsive:true,maintainAspectRatio:false}});

  var risks = ['Highest — systematic outcome failure, slow resolution','High — large volume, above-market uphold','Medium — high volume but faster resolution','Medium — moderate volume and uphold','Lower — smaller volume'];
  var tb=document.getElementById('t3');
  var sorted = D.ptable.slice().sort(function(a,b){return (b.c||0)-(a.c||0);});
  tb.innerHTML = sorted.map(function(r,i){
    var ub=r.u==null?'N/A':'<span class="'+(r.u>55?'b-r':r.u>40?'b-a':'b-g')+'">'+r.u+'%</span>';
    return '<tr><td>'+(i+1)+'</td><td>'+r.pg+'</td><td>'+fmtn(r.v)+'</td><td>'+ub+'</td><td style="color:#7c3aed;font-weight:600">'+fmtg(r.c)+'</td><td style="font-size:11px;color:#64748b">'+(risks[i]||'')+'</td></tr>';
  }).join('');

  var scens = [5,10,15,20].map(function(pct){
    var avoided = Math.round(D.mkt['2025H2']*pct/100);
    var saved   = Math.round(avoided*D.avg_cpc);
    return {pct:pct,avoided:avoided,saved:saved};
  });
  document.getElementById('scens').innerHTML = scens.map(function(s){
    return '<div class="scen"><h4>'+s.pct+'% complaint volume reduction</h4>'
      +'<p>Assumption: each avoided complaint saves approx. GBP '+fmtn(D.avg_cpc)+' (handling + FOS escalation risk + redress). Modelled, not audited.</p>'
      +'<div class="sv"><div class="n">'+fmtn(s.avoided)+'</div><div class="l">Complaints avoided</div></div>'
      +'<div class="sv p"><div class="n">'+fmtg(s.saved)+'</div><div class="l">Est. cost saving</div></div>'
      +'</div>';
  }).join('');
}
</script>
</body>
</html>"""

html = html.replace("CHARTJS_PLACEHOLDER", chartjs)
html = html.replace("DATA_PLACEHOLDER", DATA_JSON)

out = ROOT / "dashboard.html"
out.write_text(html, encoding="utf-8")
print(f"Done: {out.stat().st_size//1024}KB")
