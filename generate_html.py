import json

with open("entreprises_rge_details.json", "r") as f:
    data = json.load(f)

rows = []
for idx, e in enumerate(data):
    g = e.get("google")
    if g and g.get("total_reviews") is not None:
        rows.append({
            "orig_idx": idx + 1,
            "name": e["name"],
            "sector": e.get("sector", ""),
            "total_reviews": g["total_reviews"],
            "rating": g.get("rating"),
            "match_score": g.get("match_score", 0),
            "google_name": g.get("name", ""),
        })

rows_json = json.dumps(rows, ensure_ascii=False, indent=2)

html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Artisans RGE - Muretain Agglo</title>
<style>
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 2rem;
    background: #1a1a2e;
    color: #e0e0e0;
  }}
  h1 {{
    text-align: center;
    color: #fff;
    margin-bottom: 0.2rem;
  }}
  .subtitle {{
    text-align: center;
    color: #aaa;
    margin-bottom: 1.5rem;
    font-size: 0.9rem;
  }}
  .stats {{
    display: flex;
    justify-content: center;
    gap: 2rem;
    margin-bottom: 1.5rem;
    flex-wrap: wrap;
  }}
  .stat-box {{
    background: #16213e;
    border: 1px solid #0f3460;
    border-radius: 8px;
    padding: 0.8rem 1.5rem;
    text-align: center;
  }}
  .stat-box .val {{
    font-size: 1.6rem;
    font-weight: bold;
    color: #e94560;
  }}
  .stat-box .lbl {{
    font-size: 0.75rem;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }}
  #search {{
    display: block;
    margin: 0 auto 1.2rem;
    padding: 0.6rem 1rem;
    width: 400px;
    max-width: 90%;
    border: 1px solid #0f3460;
    border-radius: 6px;
    background: #16213e;
    color: #e0e0e0;
    font-size: 0.95rem;
  }}
  #search::placeholder {{ color: #666; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    background: #16213e;
    border-radius: 8px;
    overflow: hidden;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }}
  th {{
    background: #0f3460;
    color: #fff;
    padding: 0.75rem 1rem;
    text-align: left;
    cursor: pointer;
    user-select: none;
    position: relative;
    white-space: nowrap;
  }}
  th:hover {{ background: #1a4a7a; }}
  th .arrow {{ margin-left: 0.3rem; font-size: 0.7rem; }}
  td {{
    padding: 0.6rem 1rem;
    border-bottom: 1px solid #1a2744;
  }}
  tr:hover td {{ filter: brightness(1.15); }}
  .rating-stars {{ color: #f5c518; }}
  .match-badge {{
    display: inline-block;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-weight: bold;
    font-size: 0.85rem;
  }}
  footer {{
    text-align: center;
    color: #555;
    margin-top: 1.5rem;
    font-size: 0.8rem;
  }}
</style>
</head>
<body>

<h1>Artisans RGE - Muretain Agglo 2026</h1>
<p class="subtitle">{len(rows)} artisans avec avis Google</p>

<div class="stats">
  <div class="stat-box"><div class="val">{len(rows)}</div><div class="lbl">Artisans</div></div>
  <div class="stat-box"><div class="val" id="avgRating">-</div><div class="lbl">Note moyenne</div></div>
  <div class="stat-box"><div class="val" id="avgMatch">-</div><div class="lbl">Match moyen</div></div>
</div>

<input type="text" id="search" placeholder="Rechercher un artisan..." oninput="filterTable()">

<table>
  <thead>
    <tr>
      <th onclick="sortTable(0,'num')">N° liste <span class="arrow"></span></th>
      <th onclick="sortTable(1,'str')">Nom de l'artisan <span class="arrow"></span></th>
      <th onclick="sortTable(2,'str')">Secteur <span class="arrow"></span></th>
      <th onclick="sortTable(3,'num')">Avis Google <span class="arrow"></span></th>
      <th onclick="sortTable(4,'num')">Note <span class="arrow"></span></th>
      <th onclick="sortTable(5,'num')">Match Score <span class="arrow"></span></th>
    </tr>
  </thead>
  <tbody id="tbody">
  </tbody>
</table>

<footer>Données issues de Google Places API - Mise à jour 2026</footer>

<script>
const DATA = {rows_json};

function matchColor(score) {{
  const ratio = score / 5;
  const r = Math.round(220 - ratio * 190);
  const g = Math.round(50 + ratio * 180);
  const b = Math.round(50);
  return `rgb(${{r}},${{g}},${{b}})`;
}}

function starsHTML(rating) {{
  if (rating === null) return '<span style="color:#666">N/A</span>';
  const full = Math.floor(rating);
  const half = rating % 1 >= 0.5 ? 1 : 0;
  let s = '<span class="rating-stars">';
  for (let i = 0; i < full; i++) s += '★';
  if (half) s += '½';
  s += '</span> ' + rating.toFixed(1);
  return s;
}}

function renderTable(data) {{
  const tbody = document.getElementById('tbody');
  tbody.innerHTML = '';
  data.forEach((r, i) => {{
    const tr = document.createElement('tr');
    const bgColor = matchColor(r.match_score);
    tr.style.borderLeft = `4px solid ${{bgColor}}`;
    tr.style.background = `linear-gradient(90deg, ${{bgColor}}22 0%, #16213e 40%)`;
    tr.innerHTML = `
      <td>${{r.orig_idx}}</td>
      <td><strong>${{r.name}}</strong></td>
      <td>${{r.sector}}</td>
      <td>${{r.total_reviews}}</td>
      <td>${{starsHTML(r.rating)}}</td>
      <td><span class="match-badge" style="background:${{bgColor}}; color:#fff">${{r.match_score}} / 5</span></td>
    `;
    tbody.appendChild(tr);
  }});
  updateStats(data);
}}

function updateStats(data) {{
  const withRating = data.filter(r => r.rating !== null);
  const avg = withRating.length ? (withRating.reduce((a, r) => a + r.rating, 0) / withRating.length).toFixed(2) : '-';
  const avgM = data.length ? (data.reduce((a, r) => a + r.match_score, 0) / data.length).toFixed(1) : '-';
  document.getElementById('avgRating').textContent = avg;
  document.getElementById('avgMatch').textContent = avgM + ' / 5';
}}

let sortCol = -1;
let sortAsc = true;

function sortTable(col, type) {{
  if (sortCol === col) {{ sortAsc = !sortAsc; }}
  else {{ sortCol = col; sortAsc = true; }}

  const keys = ['orig_idx','name','sector','total_reviews','rating','match_score'];
  DATA.sort((a, b) => {{
    let va, vb;
    va = a[keys[col]]; vb = b[keys[col]];
    if (va === null || va === undefined) va = type === 'num' ? -Infinity : '';
    if (vb === null || vb === undefined) vb = type === 'num' ? -Infinity : '';
    if (type === 'num') {{ return sortAsc ? va - vb : vb - va; }}
    return sortAsc ? String(va).localeCompare(String(vb), 'fr') : String(vb).localeCompare(String(va), 'fr');
  }});

  document.querySelectorAll('th .arrow').forEach(a => a.textContent = '');
  document.querySelectorAll('th')[col].querySelector('.arrow').textContent = sortAsc ? '▲' : '▼';
  renderTable(DATA);
}}

function filterTable() {{
  const q = document.getElementById('search').value.toLowerCase();
  const filtered = DATA.filter(r => r.name.toLowerCase().includes(q) || r.sector.toLowerCase().includes(q) || String(r.orig_idx).includes(q));
  renderTable(filtered);
}}

renderTable(DATA);
</script>
</body>
</html>"""

with open("output.html", "w") as f:
    f.write(html)

print(f"output.html généré avec {len(rows)} artisans")
