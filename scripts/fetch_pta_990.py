"""Parent organizations' finances from their IRS Form 990 filings: for every PPS school on the explorer, the PTAs,
PTOs, school foundations, "friends of" groups and booster clubs found in ProPublica's Nonprofit Explorer
(https://projects.propublica.org/nonprofits/, data from the IRS e-filed 990, 990-EZ and 990-PF returns), with each
filing's revenue, contributions, fundraising, expenses and net assets.
Most Oregon PTAs are chapters filed as "PTA Oregon Congress" with the school in the organization's sub-name. A match
needs: an Oregon organization in Portland, the school's name in its name or sub-name as a whole word, and a parent-
group word (PTA, PTO, parent, foundation, friends, booster, school). Common-word names (Grant, Lincoln, Scott ...) are
also required to carry "PTA" or the school's full name, and every match is listed for review.
Small groups that file only the 990-N e-Postcard (gross receipts normally $50,000 or less) report no dollar amounts.
Each group's newest return may come only from the IRS master-file summary (form 'IRS summary': revenue, gross receipts,
assets).
Output: source/pta/pta-990.json (organizations by school, with filings) and source/pta/pta-990-filings.csv
"""
import csv, json, os, re, sys, time, unicodedata, urllib.parse
import requests
sys.stdout.reconfigure(encoding='utf-8', line_buffering=True)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'source', 'pta'); os.makedirs(OUT, exist_ok=True)
CACHE = os.path.join(OUT, 'cache'); os.makedirs(CACHE, exist_ok=True)
PAGE = os.path.join(ROOT, 'rightsizing-scenario-explorer.html')
API = 'https://projects.propublica.org/nonprofits/api/v2'
UA = {'User-Agent': 'pps-rightsizing-analysis/1.0 (personal research, low volume)'}
D = json.loads(re.search(r'const D = (\{.*?\});\nconst esc', open(PAGE, encoding='utf-8').read(), re.S).group(1))

def get(url, key):
    p = os.path.join(CACHE, re.sub(r'[^A-Za-z0-9_.-]', '_', key)[:150] + '.json')
    if os.path.exists(p): return json.load(open(p, encoding='utf-8'))
    for i in range(4):
        r = requests.get(url, headers=UA, timeout=60)
        if r.status_code == 200:
            d = r.json(); json.dump(d, open(p, 'w', encoding='utf-8')); time.sleep(0.6); return d
        if r.status_code == 404: json.dump({}, open(p, 'w')); return {}
        time.sleep(3 * (i + 1))
    return {}

def n(s): return unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
GROUP = re.compile(r'\b(pta|pto|ptsa|parent|parents|foundation|friends|booster|boosters|school|schools)\b')
# names that are also common words or surnames: require PTA / the full school name
COMMON = {'Grant', 'Lincoln', 'Scott', 'Lee', 'Jackson', 'Kelly', 'Lewis', 'Franklin', 'Cleveland', 'Roosevelt', 'Jefferson', 'Chapman',
          'Alameda', 'Arleta', 'Beach', 'Rigler', 'Vernon', 'Clark', 'Gray', 'George', 'Markham', 'Woodlawn', 'Peninsula', 'Atkinson',
          'Grout', 'Lane', 'Sabin', 'Whitman', 'Glencoe', 'Richmond', 'Faubion', 'Rieke', 'Bridger', 'Vestal', 'Sitton', 'Astor', 'Lent'}
ALIASES = {'Lane': ['Brentwood', 'Lane'], 'MLK Jr': ['King', 'Martin Luther King'], 'Ida B Wells-Barnett': ['Ida B Wells', 'Wilson'], 'McDaniel': ['McDaniel', 'Madison'],
           'César Chávez': ['Cesar Chavez'], 'Harriet Tubman': ['Tubman'], 'Bridger Creative Science': ['Bridger', 'Creative Science'],
           'Sunnyside Environmental': ['Sunnyside'], 'Boise-Eliot/Humboldt': ['Boise Eliot', 'Boise-Eliot'], 'Mt Tabor': ['Mt Tabor', 'Mount Tabor'],
           'Lee': ['Lee', 'Sunrise'], 'Beverly Cleary': ['Beverly Cleary', 'Fernwood', 'Hollyrood']}
# organizations that only share a name with a school (churches, parks, community centers, family foundations, clubs)
NOT_SCHOOL = re.compile(r'church|presbyterian|community (house|cent)|\bpark\b(?! elem| pta)|club foundation|king family|michael king smith|jeremy wilson|woodrow|after school care|lorene farrar', re.I)
def kind(text):
    t = n(text)
    return ('alumni' if 'alumni' in t else 'booster' if 'booster' in t or 'lacrosse' in t or 'football' in t else
            'PTA/PTO' if re.search(r'\b(pta|ptsa|pto|parent|parents|families and teachers)\b', t) else
            'foundation' if re.search(r'foundation|friends|endow', t) else 'other')
# organizations found by EIN on school / PTA web pages rather than by name (kept only if in Portland)
EXTRA = {'Astor': [455511705]}   # 41-6038339 "Kellogg Middle School PTSA" is in Rochester, MN
TYPE_WORD = {'ES': 'elementary', 'K8': 'k-8', 'MS': 'middle', 'HS': 'high'}

out, rows = {}, []
for k in sorted(D['region_of']):
    names = ALIASES.get(k, [k])
    full = (D['schools'] and next((s['name'] for s in D['schools'] if s['key'] == k), k))
    found = {}
    for nm in names:
        for q in (f'{nm} PTA', f'{nm} PTO', f'{nm} foundation', f'friends of {nm}', f'{nm} booster', nm):
            d = get(f"{API}/search.json?q={urllib.parse.quote(q)}&state%5Bid%5D=OR", f'search_{q}')
            for o in d.get('organizations', []):
                text = n(f"{o.get('name', '')} {o.get('sub_name') or ''}")
                if not re.search(r'\b' + re.escape(n(nm)) + r'\b', text): continue
                if (o.get('city') or '').upper() not in ('PORTLAND', '') : continue
                if not GROUP.search(text): continue
                if nm in COMMON and not re.search(r'\bpta|ptsa|pto\b', text) and n(full) not in text and not re.search(re.escape(n(nm)) + r' (elementary|middle|high|k-?8|school)', text): continue
                if NOT_SCHOOL.search(f"{o.get('name', '')} {o.get('sub_name') or ''}"): continue
                found[o['ein']] = o
    for ein in EXTRA.get(k, []):
        if ein not in found:
            o = get(f'{API}/organizations/{ein}.json', f'org_{ein}').get('organization', {})
            if (o.get('city') or '').upper() == 'PORTLAND': found[ein] = o
            else: print(f'  {k}: EIN {ein} is {o.get("name")} in {o.get("city")}, {o.get("state")}: not this school')
    orgs = []
    for ein, o in found.items():
        d = get(f'{API}/organizations/{ein}.json', f'org_{ein}')
        org = d.get('organization', {})
        fil = [dict(year=f.get('tax_prd_yr'), period=f.get('tax_prd'), form={0: '990', 1: '990-EZ', 2: '990-PF'}.get(f.get('formtype'), str(f.get('formtype'))),
                    revenue=f.get('totrevenue'), contributions=f.get('totcntrbs') if f.get('totcntrbs') is not None else f.get('totcntrbgfts'),
                    fundraising_gross=f.get('grsrevnuefndrsng'), fundraising_net=f.get('netincfndrsng'), expenses=f.get('totfuncexpns'),
                    net_assets=f.get('totnetassetsend'), assets=f.get('totassetsend'), pdf=f.get('pdf_url'))
               for f in d.get('filings_with_data', [])]
        # the IRS exempt-organization master file summary (ProPublica's organization record) often carries a newer
        # return than the e-file extracts: its tax period, total revenue, gross receipts and assets. Used when newer
        # than the latest detailed filing and showing revenue (a zero usually means a 990-N postcard filer).
        tp = org.get('tax_period') or ''
        if tp and (org.get('revenue_amount') or 0) > 0 and int(tp[:4] + tp[5:7]) > max([f['period'] or 0 for f in fil] or [0]):
            fil.append(dict(year=int(tp[:4]), period=int(tp[:4] + tp[5:7]), form='IRS summary', revenue=org.get('revenue_amount'), contributions=None,
                            fundraising_gross=None, fundraising_net=None, expenses=None, net_assets=None, assets=org.get('asset_amount'),
                            pdf=None, gross_receipts=org.get('income_amount')))
        no_data = sorted({(f.get('tax_prd_yr'), f.get('formtype_str') or str(f.get('formtype'))) for f in d.get('filings_without_data', [])}, reverse=True)
        label = f"{org.get('name') or o.get('name') or ''} {org.get('sub_name') or o.get('sub_name') or ''}"
        orgs.append(dict(ein=ein, kind=kind(label), name=org.get('name') or o.get('name'), sub_name=org.get('sub_name') or o.get('sub_name'), address=org.get('address'),
                         irs=f'https://apps.irs.gov/app/eos/details/?ein={ein}',
                         city=org.get('city'), ruling_date=org.get('ruling_date'), filings=fil, filings_without_data=[list(x) for x in no_data],
                         url=f'https://projects.propublica.org/nonprofits/organizations/{ein}'))
        for f in fil: rows.append(dict(school=k, ein=ein, kind=kind(label), org=label.strip(), **f, irs=f'https://apps.irs.gov/app/eos/details/?ein={ein}'))
    out[k] = orgs
    latest = [max(o['filings'], key=lambda f: f['year'] or 0) for o in orgs if o['filings']]
    print(f"{k:26s} {len(orgs)} org(s): " + '; '.join(f"{(o['sub_name'] or o['name'])[:48]}" + (f" (latest {max(o['filings'], key=lambda f: f['year'] or 0)['year']}: rev ${max(o['filings'], key=lambda f: f['year'] or 0)['revenue']:,})" if o['filings'] else ' (no 990 data)') for o in orgs))
json.dump(dict(source='ProPublica Nonprofit Explorer API (IRS Form 990 / 990-EZ / 990-PF e-file data)', fetched=time.strftime('%Y-%m-%d'), schools=out),
          open(os.path.join(OUT, 'pta-990.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
with open(os.path.join(OUT, 'pta-990-filings.csv'), 'w', encoding='utf-8', newline='') as fh:
    w = csv.DictWriter(fh, fieldnames=list(dict.fromkeys(c for r in rows for c in r)) if rows else ['school']); w.writeheader(); w.writerows(rows)
print('schools with an organization:', sum(1 for v in out.values() if v), 'of', len(out), '| filings:', len(rows))
