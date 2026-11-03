"""
ARQUIVO H.M. — Relatório da Perícia

Busca os dados públicos do seu GitHub e desenha o arquivo dist/pericia.svg.
Roda sozinho no GitHub Actions (veja .github/workflows/pericia.yml).

Para testar no seu computador sem token:  python scripts/pericia.py --exemplo
"""
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone

USUARIO = os.environ.get("GH_USER", "HellenMayara")
TOKEN = os.environ.get("GH_TOKEN")
SAIDA = "dist/pericia.svg"

CONSULTA = """
query($login: String!) {
  user(login: $login) {
    repositories(ownerAffiliations: OWNER, isFork: false, privacy: PUBLIC, first: 100) {
      totalCount
      nodes {
        name
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount } }
      }
    }
  }
}
"""


# ─────────────────────────── 1. COLETA ───────────────────────────
def buscar_dados():
    corpo = json.dumps({"query": CONSULTA, "variables": {"login": USUARIO}}).encode()
    pedido = urllib.request.Request(
        "https://api.github.com/graphql",
        data=corpo,
        headers={"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(pedido) as resposta:
        return json.load(resposta)["data"]["user"]


def dados_de_exemplo():
    # Números parecidos com os reais de nov/2026, só para ver o desenho sem token
    hoje = date(2026, 11, 3)
    dias = [{"date": (hoje - timedelta(days=i)).isoformat(), "contributionCount": 0} for i in range(365)]
    for d in dias:
        if d["date"] in ("2026-09-22", "2026-10-19", "2026-10-20"):
            d["contributionCount"] = {"2026-09-22": 1, "2026-10-19": 7, "2026-10-20": 2}[d["date"]]
    return {
        "repositories": {
            "totalCount": 3,
            "nodes": [
                {"languages": {"edges": [
                    {"size": 20632, "node": {"name": "JavaScript"}},
                    {"size": 12203, "node": {"name": "CSS"}},
                    {"size": 2981, "node": {"name": "HTML"}},
                ]}}
            ],
        },
        "contributionsCollection": {"contributionCalendar": {
            "totalContributions": 10,
            "weeks": [{"contributionDays": sorted(dias, key=lambda d: d["date"])}],
        }},
    }


# ─────────────────────────── 2. ANÁLISE ───────────────────────────
def analisar(u):
    cal = u["contributionsCollection"]["contributionCalendar"]
    dias = [d for w in cal["weeks"] for d in w["contributionDays"]]
    dias.sort(key=lambda d: d["date"])
    ativos = [d["contributionCount"] > 0 for d in dias]

    # maior sequência de dias seguidos com atividade
    maior = atual = 0
    for a in ativos:
        atual = atual + 1 if a else 0
        maior = max(maior, atual)

    # sequência atual: conta de trás para frente (hoje ainda pode estar sem commit)
    seq = 0
    pos = len(ativos) - 1
    if pos >= 0 and not ativos[pos]:
        pos -= 1
    while pos >= 0 and ativos[pos]:
        seq += 1
        pos -= 1

    # linguagens somando o tamanho do código de todos os repositórios
    bytes_por_ling = {}
    for repo in u["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            nome = e["node"]["name"]
            bytes_por_ling[nome] = bytes_por_ling.get(nome, 0) + e["size"]
    total = sum(bytes_por_ling.values()) or 1
    langs = sorted(bytes_por_ling.items(), key=lambda x: -x[1])[:4]
    langs = [(n, b / total * 100) for n, b in langs]

    return {
        "repos": u["repositories"]["totalCount"],
        "contrib": cal["totalContributions"],
        "dias": sum(ativos),
        "seq": seq,
        "maior": maior,
        "langs": langs,
    }


# ─────────────────────────── 3. DESENHO ───────────────────────────
CORES = ["#c0281f", "#e0a43a", "#6b9bd1", "#8fae7e"]


def desenhar(r, exemplo=False):
    agora = datetime.now(timezone(timedelta(hours=-3)))
    rotulo_data = "dados de exemplo" if exemplo else f"atualizado em {agora:%d/%m/%Y}"

    itens = [
        ("REPOSITÓRIOS ANALISADOS", str(r["repos"])),
        ("CONTRIBUIÇÕES NO ÚLTIMO ANO", str(r["contrib"])),
        ("DIAS COM ATIVIDADE", str(r["dias"])),
        ("SEQUÊNCIA ATUAL", f'{r["seq"]} {"dia" if r["seq"] == 1 else "dias"}'),
        ("MAIOR SEQUÊNCIA", f'{r["maior"]} {"dia" if r["maior"] == 1 else "dias"}'),
    ]

    css, linhas = [], []
    for i, (rot, val) in enumerate(itens):
        y = 108 + i * 34
        a, b = 6 + i * 7, 10 + i * 7          # % do ciclo em que o valor "aparece"
        pontos = "." * (30 - len(rot))
        css.append(f".v{i}{{animation:v{i} 12s infinite}}"
                   f"@keyframes v{i}{{0%,{a}%{{opacity:0}}{b}%,96%{{opacity:1}}100%{{opacity:0}}}}")
        linhas.append(
            f'<text x="40" y="{y}" font-size="13" fill="#8f897d">{rot} <tspan fill="#4a4d52">{pontos}</tspan></text>'
            f'<text class="v{i}" x="420" y="{y}" text-anchor="end" font-size="18" font-weight="700" fill="#efe7d4">{val}</text>'
        )

    barras = []
    for i, (nome, pct) in enumerate(r["langs"]):
        y = 196 + i * 26
        larg = max(4, 250 * pct / 100)
        a = 40 + i * 6
        css.append(f".b{i}{{transform-box:fill-box;transform-origin:left center;animation:b{i} 12s infinite}}"
                   f"@keyframes b{i}{{0%,{a}%{{transform:scaleX(0)}}{a+10}%,96%{{transform:scaleX(1)}}100%{{transform:scaleX(0)}}}}")
        barras.append(
            f'<text x="480" y="{y}" font-size="12" fill="#d8d2c4">{nome}</text>'
            f'<rect x="580" y="{y-10}" width="250" height="12" rx="2" fill="#24272b"/>'
            f'<rect class="b{i}" x="580" y="{y-10}" width="{larg:.1f}" height="12" rx="2" fill="{CORES[i % 4]}"/>'
            f'<text x="870" y="{y}" text-anchor="end" font-size="12" fill="#8f897d">{pct:.0f}%</text>'
        )

    # Hélice de DNA: duas ondas e degraus coloridos conforme as linguagens.
    # Desenho 2 voltas e desloco 1 volta para a esquerda em loop = parece girar.
    import math
    per, amp, cx0, cy = 100, 22, 470, 120
    onda1 = " ".join(f"{cx0 + x},{cy + amp * math.sin(2 * math.pi * x / per):.1f}" for x in range(0, 2 * per + 1, 4))
    onda2 = " ".join(f"{cx0 + x},{cy - amp * math.sin(2 * math.pi * x / per):.1f}" for x in range(0, 2 * per + 1, 4))
    # cada linguagem ganha degraus proporcionais à sua porcentagem
    tons = []
    for i, (nome, pct) in enumerate(r["langs"]):
        tons += [CORES[i % 4]] * max(1, round(pct / 10))
    tons = tons or ["#c0281f"]
    degraus = []
    for k, x in enumerate(range(0, 2 * per, 10)):
        y1 = cy + amp * math.sin(2 * math.pi * x / per)
        y2 = cy - amp * math.sin(2 * math.pi * x / per)
        degraus.append(f'<line x1="{cx0 + x}" y1="{y1:.1f}" x2="{cx0 + x}" y2="{y2:.1f}" stroke="{tons[k % len(tons)]}" stroke-width="3"/>')
    helice = "".join(degraus) + (
        f'<polyline points="{onda1}" fill="none" stroke="#d8d2c4" stroke-width="2.5"/>'
        f'<polyline points="{onda2}" fill="none" stroke="#8f897d" stroke-width="2.5"/>'
    )
    # 4 cópias lado a lado para cobrir a janela enquanto desliza
    helices = "".join(f'<g transform="translate({k * 2 * per},0)">{helice}</g>' for k in range(3))

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="900" height="320" viewBox="0 0 900 320">
<!-- ARQUIVO H.M. — RELATÓRIO DA PERÍCIA (gerado por scripts/pericia.py) -->
<defs>
  <clipPath id="tubo"><rect x="470" y="88" width="400" height="64" rx="8"/></clipPath>
  <linearGradient id="vidro" x1="0" x2="1">
    <stop offset="0" stop-color="#17191c"/><stop offset=".12" stop-color="#17191c" stop-opacity="0"/>
    <stop offset=".88" stop-color="#17191c" stop-opacity="0"/><stop offset="1" stop-color="#17191c"/>
  </linearGradient>
</defs>
<style>
text{{font-family:'Courier New',Courier,monospace}}
{"".join(css)}
.dna{{animation:dna 4s linear infinite}}@keyframes dna{{to{{transform:translateX(-200px)}}}}
.scan{{animation:scan 3s ease-in-out infinite alternate}}@keyframes scan{{from{{transform:translateX(0)}}to{{transform:translateX(390px)}}}}
.rec{{animation:rec 1.2s steps(1) infinite}}@keyframes rec{{50%{{opacity:0}}}}
@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}
</style>

<rect width="900" height="320" rx="10" fill="#17191c"/>
<rect x=".5" y=".5" width="899" height="319" rx="10" fill="none" stroke="#2f3338"/>

<!-- cabeçalho do laudo -->
<text x="40" y="44" font-size="20" font-weight="700" fill="#efe7d4" letter-spacing="3">RELATÓRIO DA PERÍCIA</text>
<text x="40" y="66" font-size="11" fill="#b3261e" letter-spacing="2">LAUDO Nº 001 · ANALISADO: github.com/{USUARIO}</text>
<circle class="rec" cx="852" cy="39" r="5" fill="#d0443a"/>
<text x="840" y="44" text-anchor="end" font-size="11" fill="#8f897d">AO VIVO</text>
<line x1="40" y1="78" x2="860" y2="78" stroke="#2f3338"/>

<!-- coluna da esquerda: números -->
{"".join(linhas)}

<!-- coluna da direita: DNA do código -->
<rect x="470" y="88" width="400" height="64" rx="8" fill="#101214" stroke="#2f3338"/>
<g clip-path="url(#tubo)"><g class="dna">{helices}</g>
  <rect class="scan" x="472" y="88" width="6" height="64" fill="#e0443a" opacity=".35"/></g>
<rect x="470" y="88" width="400" height="64" rx="8" fill="url(#vidro)"/>
<text x="470" y="172" font-size="12" font-weight="700" fill="#efe7d4" letter-spacing="2">AMOSTRAS DE DNA DO CÓDIGO</text>
{"".join(barras)}

<text x="40" y="300" font-size="10.5" fill="#5b5f66">{rotulo_data} · gerado automaticamente pelo GitHub Actions</text>
</svg>
"""


if __name__ == "__main__":
    exemplo = "--exemplo" in sys.argv or not TOKEN
    usuario = dados_de_exemplo() if exemplo else buscar_dados()
    os.makedirs("dist", exist_ok=True)
    with open(SAIDA, "w", encoding="utf-8") as f:
        f.write(desenhar(analisar(usuario), exemplo))
    print("Relatório salvo em", SAIDA)
