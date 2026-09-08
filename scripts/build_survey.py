"""A single-file survey for collecting a human's keep/cut calls, blind.

`docs/FINDINGS.md` #69 established that this model does NOT beat the league's
owners out of sample. That makes a good owner a better benchmark than the model,
and it makes his calls worth collecting properly rather than discussing. This
builds `out/keeper_survey.html`: one page, no server, opens on a phone, one
player at a time.

THE DESIGN RULE, WHICH IS THE WHOLE POINT

**The survey shows no model output.** No dollar value, no surplus, no keep flag,
no roto points. A reviewer shown a number reviews that number; a reviewer asked
cold produces an independent estimate, and only the second can be scored against
the model or against another reviewer. What it does show is what a human needs
to decide: the contract, the price, the season he just had, and the season he is
projected for. The projection is shown because the question is "given this
outlook, keep or cut", not "guess the projection".

WHAT IT ASKS

  1. Keep or cut, in a vacuum -- ignoring roster limits and budget, just
     "is this contract worth its price".
  2. If cut: what he goes for at the auction. Josh's framing, and it halves the
     work, since a kept player never hits the block.
  3. For a short list of PRICE CHECK players, the auction price is asked either
     way. These are the biggest gaps between what the model thinks a player is
     worth and what it expects him to cost, and 20 of the top 25 are pitchers.
     That claim is the model's most falsifiable and needs an outside number
     whether or not the reviewer would keep the man.

ORDER: HIGHEST INFORMATION FIRST

A reviewer will not finish 240 players, so the ones that change the most should
come first. The score combines, in rough order of weight:
  - whether the model's own call FLIPS on the playing-time assumption, which is
    the one input a human has and the projection does not (44 players);
  - how close the call is, scaled by the dollars at stake, since a marginal
    $22 contract is worth more of his attention than an obvious $1 one;
  - the model's own uncertainty, where the bootstrap already says it is unsure.
Each player carries the reason he was ranked where he was, so the reviewer can
see he is not being asked about noise.

    PYTHONPATH=.:scripts python3 scripts/build_survey.py
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from klab import config as C
from klab.project import lines_2026_hitters, lines_2026_pitchers

OUT = C.OUT / "keeper_survey.html"
N_PRICE_CHECK = 18


def _fmt(v, dp=0):
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return None
    return round(float(v), dp)


def build_players() -> list[dict]:
    board = pd.read_csv(C.OUT / "keeper_board_2027.csv")
    params = json.loads((C.OUT / "model_params.json").read_text())
    icept = params["exchange_rate"]["intercept"]
    usd = params["exchange_rate"]["usd_per_point"]

    b = board[board["keepable"].fillna(False).astype(bool)].copy()
    b = b[b["keeper_cost"].notna()]

    # The playing-time flip: does the model's own call depend on an assumption
    # only a human can resolve? This is the highest-information flag there is.
    s_proj = ((b["roto_points"] - icept) * usd).clip(lower=0) - b["keeper_cost"]
    s_ft = ((b["roto_points_ft"].fillna(b["roto_points"]) - icept) * usd
            ).clip(lower=0) - b["keeper_cost"]
    b["pt_flip"] = ((s_proj <= 0) & (s_ft > 0)) | ((s_proj > 0) & (s_ft <= 0))

    # Closeness to the decision boundary, in dollars, scaled by what is at risk.
    surplus = b["surplus_multiyear"].fillna(0.0)
    closeness = 1.0 / (1.0 + surplus.abs() / 8.0)
    unsure = 1.0 - (b["p_surplus_positive"].fillna(0.5) - 0.5).abs() * 2.0
    b["info"] = (b["keeper_cost"] * (0.35 + closeness)
                 + 45.0 * b["pt_flip"].astype(float)
                 + 12.0 * unsure)

    # Price-check list: the model's biggest bargain claims, asked either way.
    gap = (b["production_value"] - b["market_price"]).fillna(-1e9)
    price_ids = set(b.loc[gap.nlargest(N_PRICE_CHECK).index, "fg_id"])

    h26 = lines_2026_hitters().set_index("fg_id")
    p26 = lines_2026_pitchers().set_index("fg_id")

    def reason(r):
        if r["pt_flip"]:
            return "the call flips on how much he plays"
        if r["fg_id"] in price_ids:
            return "price check: the model thinks the room underpays here"
        if abs(r["surplus_multiyear"] or 0) < 6:
            return f"close call with ${r['keeper_cost']:.0f} at stake"
        if (r["p_surplus_positive"] or 1) < 0.75:
            return "the model is not confident here"
        return f"${r['keeper_cost']:.0f} contract"

    out = []
    for r in b.sort_values("info", ascending=False).itertuples():
        d = {k: getattr(r, k) for k in ("fg_id", "name", "team", "role", "contract")}
        d["fg_id"] = int(d["fg_id"])
        d["cost"] = _fmt(r.keeper_cost)
        d["ask_price"] = int(r.fg_id) in price_ids
        d["why"] = reason({"pt_flip": r.pt_flip, "fg_id": int(r.fg_id),
                           "surplus_multiyear": r.surplus_multiyear,
                           "keeper_cost": r.keeper_cost,
                           "p_surplus_positive": r.p_surplus_positive})
        hit = r.role != "PIT"
        if hit and int(r.fg_id) in h26.index:
            a = h26.loc[int(r.fg_id)]
            avg = (a["H"] / a["AB"]) if a["AB"] else None
            d["y26"] = {"PA": _fmt(a["PA"]), "HR": _fmt(a["HR"]), "R": _fmt(a["R"]),
                        "RBI": _fmt(a["RBI"]), "SB": _fmt(a["SB"]), "AVG": _fmt(avg, 3)}
        elif not hit and int(r.fg_id) in p26.index:
            a = p26.loc[int(r.fg_id)]
            era = (a["ER"] * 9 / a["IP"]) if a["IP"] else None
            whip = ((a["BB"] + a["H"]) / a["IP"]) if a["IP"] else None
            d["y26"] = {"IP": _fmt(a["IP"]), "W": _fmt(a["W"]), "SV": _fmt(a["SV"]),
                        "K": _fmt(a["K"]), "ERA": _fmt(era, 2), "WHIP": _fmt(whip, 2)}
        else:
            d["y26"] = None
        d["y27"] = ({"PA": _fmt(r.PA), "HR": _fmt(r.HR), "R": _fmt(r.R),
                     "RBI": _fmt(r.RBI), "SB": _fmt(r.SB), "AVG": _fmt(r.AVG, 3)}
                    if hit else
                    {"IP": _fmt(r.IP), "W": _fmt(r.W), "SV": _fmt(r.SV),
                     "K": _fmt(r.K), "ERA": _fmt(r.ERA, 2), "WHIP": _fmt(r.WHIP, 2)})
        out.append(d)
    return out


HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Keeper survey 2027</title>
<style>
:root{--bg:#11161c;--panel:#1a222b;--ink:#e8eef4;--dim:#8fa3b5;--line:#2a3642;
      --pos:#4ec98b;--neg:#ef7676;--accent:#5aa9e6}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
     font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:14px 16px;border-bottom:1px solid var(--line);position:sticky;top:0;
       background:var(--bg);z-index:5}
h1{margin:0;font-size:16px;font-weight:600}
.sub{color:var(--dim);font-size:12px;margin-top:3px}
main{max-width:640px;margin:0 auto;padding:16px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:18px}
.pname{font-size:23px;font-weight:650;letter-spacing:-.2px}
.meta{color:var(--dim);font-size:13px;margin-top:4px}
.why{margin:14px 0 4px;padding:8px 11px;background:#16202a;border-left:3px solid var(--accent);
     border-radius:0 6px 6px 0;font-size:13px;color:#bcd0e0}
table{width:100%;border-collapse:collapse;margin-top:14px;font-size:14px}
th,td{padding:6px 4px;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left;color:var(--dim)}
thead th{color:var(--dim);font-weight:500;font-size:12px}
.cost{font-size:17px;margin:16px 0 6px}
.cost b{font-size:26px}
.btns{display:flex;gap:10px;margin-top:12px}
button{flex:1;padding:15px;font-size:16px;font-weight:600;border-radius:10px;
       border:1px solid var(--line);background:#222d38;color:var(--ink);cursor:pointer}
button:hover{border-color:var(--accent)}
.keep{background:#1d3d2e;border-color:#2f6a4d}
.cut{background:#3d2222;border-color:#6a3232}
.price{margin-top:16px;display:none}
.price.on{display:block}
.price label{display:block;font-size:14px;margin-bottom:7px;color:#cfe0ee}
.row{display:flex;gap:8px;align-items:center}
input[type=number]{flex:1;padding:13px;font-size:17px;border-radius:9px;
                   border:1px solid var(--line);background:#131b23;color:var(--ink)}
.small{padding:11px 14px;font-size:14px;flex:0 0 auto}
.bar{height:4px;background:var(--line);border-radius:2px;overflow:hidden;margin-top:10px}
.fill{height:100%;background:var(--accent);width:0}
.nav{display:flex;justify-content:space-between;margin-top:14px;font-size:13px}
.nav a{color:var(--dim);cursor:pointer;text-decoration:none}
.nav a:hover{color:var(--ink)}
textarea{width:100%;height:190px;margin-top:10px;padding:11px;border-radius:9px;
         border:1px solid var(--line);background:#131b23;color:var(--ink);
         font:12px/1.45 ui-monospace,SFMono-Regular,Menlo,monospace}
.done{text-align:center;padding:30px 0}
.tag{display:inline-block;padding:2px 7px;border-radius:5px;background:#243140;
     font-size:11px;color:#bcd0e0;margin-left:6px;vertical-align:middle}
</style></head><body>
<header>
  <h1>2027 keeper survey</h1>
  <div class="sub" id="sub">who is answering?</div>
  <div class="bar"><div class="fill" id="fill"></div></div>
</header>
<main id="app"></main>
<script>
const P = __PLAYERS__;
const KEY = "keepersurvey.v1";
let S = JSON.parse(localStorage.getItem(KEY) || "null")
        || {who:"", i:0, ans:{}};
function save(){ localStorage.setItem(KEY, JSON.stringify(S)); }
const $ = id => document.getElementById(id);
const esc = s => String(s??"").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function statTable(a, b, keys){
  const head = keys.map(k=>`<th>${k}</th>`).join("");
  const row = (lbl,o) => `<tr><td>${lbl}</td>` +
    keys.map(k=>`<td>${o && o[k]!=null ? o[k] : "&mdash;"}</td>`).join("") + "</tr>";
  return `<table><thead><tr><th></th>${head}</tr></thead><tbody>
    ${row("2026 actual", a)}${row("2027 projected", b)}</tbody></table>`;
}

function view(){
  if(!S.who) return askName();
  if(S.i >= P.length) return done();
  const p = P[S.i], a = S.ans[p.fg_id] || {};
  $("fill").style.width = (100*S.i/P.length) + "%";
  $("sub").textContent = `${esc(S.who)} · player ${S.i+1} of ${P.length} · answers save automatically`;
  const keys = p.role === "PIT" ? ["IP","W","SV","K","ERA","WHIP"]
                                : ["PA","HR","R","RBI","SB","AVG"];
  const askPrice = a.keep === false || p.ask_price;
  $("app").innerHTML = `<div class="card">
    <div class="pname">${esc(p.name)}<span class="tag">${p.role === "PIT" ? "P" : "H"}</span></div>
    <div class="meta">${esc(p.team)} &middot; contract code ${esc(p.contract)}</div>
    <div class="why">${esc(p.why)}</div>
    ${statTable(p.y26, p.y27, keys)}
    <div class="cost">Keeping him costs <b>$${p.cost}</b></div>
    <div class="meta">Ignore roster limits and budget. Is this contract worth that price?</div>
    <div class="btns">
      <button class="keep" onclick="ans(true)">Keep${a.keep===true?" &check;":""}</button>
      <button class="cut" onclick="ans(false)">Cut${a.keep===false?" &check;":""}</button>
    </div>
    <div class="price ${askPrice?"on":""}" id="pricebox">
      <label>${a.keep===false ? "If he goes back in the pool, what does he cost at the auction?"
                              : "Bonus: if he were in the auction, what would he go for?"}</label>
      <div class="row">
        <input type="number" id="pr" min="0" max="120" step="1" placeholder="$"
               value="${a.price!=null?a.price:""}" oninput="setPrice(this.value)">
        <button class="small" onclick="next()">Next &rarr;</button>
      </div>
    </div>
    <div class="nav">
      <a onclick="back()">&larr; back</a>
      <a onclick="skip()">skip</a>
      <a onclick="S.i=P.length;save();view()">finish &amp; export</a>
    </div>
  </div>`;
}
function ans(keep){
  const p = P[S.i];
  S.ans[p.fg_id] = Object.assign({}, S.ans[p.fg_id], {keep, name:p.name, cost:p.cost});
  save();
  // a cut always needs a price, and the price-check list is asked either way
  if(keep === false || p.ask_price){ view(); setTimeout(()=>{const e=$("pr"); if(e) e.focus();},30); }
  else next();
}
function setPrice(v){
  const p = P[S.i];
  S.ans[p.fg_id] = Object.assign({}, S.ans[p.fg_id], {price: v===""?null:Number(v)});
  save();
}
function next(){ S.i++; save(); view(); window.scrollTo(0,0); }
function back(){ if(S.i>0) S.i--; save(); view(); window.scrollTo(0,0); }
function skip(){ next(); }
function askName(){
  $("app").innerHTML = `<div class="card">
    <div class="pname">Who is answering?</div>
    <div class="meta" style="margin-top:10px">Your calls are compared against the model and
      against the other reviewer, so they need a name on them. Nothing leaves this device
      until you paste the results back.</div>
    <div class="row" style="margin-top:16px">
      <input type="number" style="display:none">
      <input id="nm" placeholder="your name" style="flex:1;padding:13px;font-size:16px;
        border-radius:9px;border:1px solid var(--line);background:#131b23;color:var(--ink)">
      <button class="small" onclick="setName()">Start</button>
    </div>
    <div class="meta" style="margin-top:14px">${P.length} players, hardest and most valuable
      first. Stop whenever you like; partial answers are still useful.</div>
  </div>`;
}
function setName(){ const v=$("nm").value.trim(); if(!v) return; S.who=v; save(); view(); }
function done(){
  $("fill").style.width = "100%";
  const n = Object.values(S.ans).filter(a=>a.keep!=null).length;
  const payload = JSON.stringify({who:S.who, answered:n, at:new Date().toISOString(),
                                  answers:S.ans}, null, 0);
  $("sub").textContent = `${esc(S.who)} · ${n} answered`;
  $("app").innerHTML = `<div class="card"><div class="done">
      <div class="pname">Thanks &mdash; ${n} answered</div>
      <div class="meta" style="margin-top:8px">Copy the text below and send it back.</div>
    </div>
    <div class="btns">
      <button onclick="copyOut()">Copy answers</button>
      <button onclick="S.i=0;save();view()">Go back through them</button>
    </div>
    <textarea id="out" readonly>${esc(payload)}</textarea>
  </div>`;
}
function copyOut(){
  const t = $("out"); t.select(); t.setSelectionRange(0, 999999);
  navigator.clipboard.writeText(t.value).then(
    ()=>{ document.querySelector(".btns button").textContent = "Copied \\u2713"; },
    ()=>{ document.execCommand("copy"); });
}
view();
</script></body></html>
"""


def main() -> None:
    players = build_players()
    html = HTML.replace("__PLAYERS__", json.dumps(players, separators=(",", ":")))
    OUT.write_text(html)
    n_flip = sum(1 for p in players if "flips on how much" in p["why"])
    n_price = sum(1 for p in players if p["ask_price"])
    print(f"wrote {OUT}  ({len(html)//1024} KB)")
    print(f"  {len(players)} keepable players, highest information first")
    print(f"  {n_flip} lead with the playing-time flip, {n_price} on the price-check list")
    print("  first ten:")
    for p in players[:10]:
        print(f"    {p['name']:<24} ${p['cost']:>3.0f}  {p['why']}")


if __name__ == "__main__":
    main()
