"""每週更新 index.html 內的榮家床位與衛福部長照新聞（直接改網頁裡的資料，不需重建）"""
import json, re, html, time, datetime, urllib.request
from email.utils import parsedate_to_datetime

UA = {'User-Agent': 'Mozilla/5.0 (ltc-directory)'}
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read().decode('utf-8', 'ignore')
H = open('index.html', encoding='utf-8').read()
TODAY = datetime.date.today().isoformat()

def js_block(start, end):
    i = H.index(start) + len(start); j = H.index(end, i); return i, j

# ---------- 1. 榮家床位 ----------
try:
    WANT = {'臺北榮譽國民之家': '臺北', '板橋榮譽國民之家': '板橋', '桃園榮譽國民之家': '桃園', '八德榮譽國民之家': '八德'}
    cells = lambda r: [re.sub(r'<[^>]+>|\s+', ' ', html.unescape(c)).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', r, re.S)]
    num = lambda s: int(re.match(r'-?\d+', s).group()) if re.match(r'-?\d+', s) else None
    homes, seen = {}, set()
    for p in range(1, 30):
        rows = [cells(r) for r in re.findall(r'<tr[^>]*>(.*?)</tr>', get(f'https://www.vac.gov.tw/lp-1792-1-{p}-20.html'), re.S)]
        rows = [r for r in rows if len(r) == 8 and r[0].rstrip('.').isdigit()]
        new = [r for r in rows if (r[7], r[1]) not in seen]
        if not new: break
        for r in new:
            seen.add((r[7], r[1]))
            if r[7] in WANT:
                homes.setdefault(WANT[r[7]], []).append({'type': r[1], 'open': num(r[2]), 'res': num(r[3]), 'proc': num(r[4]),
                                                         'wait': num(r[5]), 'avail': num(r[6]), 'memo': re.sub(r'^-?\d+', '', r[6]).strip('()（） ')})
        time.sleep(1)
    if len(homes) >= 3:
        i, j = js_block('window.__DATA=', ';</script>')
        data = json.loads(H[i:j].replace('<\\/', '</'))
        n = 0
        for d in data:
            m = re.search(r'(臺北|桃園|八德|板橋)榮譽國民之家', d.get('name', ''))
            if d.get('kind') == '榮民之家' and m and m.group(1) in homes:
                d['vbeds'] = {'upd': TODAY, 'rows': homes[m.group(1)]}; n += 1
        H = H[:i] + json.dumps(data, ensure_ascii=False, separators=(',', ':')).replace('</', '<\\/') + H[j:]
        print('榮家床位更新', n)
except Exception as e:
    print('榮家床位失敗，沿用舊資料：', e)

# ---------- 2. 衛福部長照新聞 ----------
try:
    REL = re.compile(r'長照|照顧|照護|安養|養護|護理之家|失智|失能|看護|喘息|日照|老人|長者|高齡|銀髮|身障|身心障礙|輔具|臥床|住宿式|社福|社會福利')
    CAT = [('政策補助', r'補助|給付|津貼|3\.0|新制|方案|預算|費用'), ('機構與稽查', r'機構|稽查|評鑑|裁罰|查核|安全|火'), ('失智與照顧', r'失智|照顧者|喘息|日照|看護|照顧')]
    i, j = js_block('let NEWS=', ';let NCAT=')
    news = json.loads(H[i:j].replace('<\\/', '</'))
    seen = {x['u']: x for x in news.get('items', [])}
    cut = time.time() - 125 * 86400
    for p in range(1, 6):
        L = re.findall(r'<a href="(https://www\.mohw\.gov\.tw/cp-16-\d+-1\.html)" title="([^"]+)"><p>.*?</p><time>(\d+)-(\d+)-(\d+)</time>', get(f'https://www.mohw.gov.tw/lp-16-1-{p}-20.html'), re.S)
        if not L: break
        for u, t, y, mo, dd in L:
            t = html.unescape(t); ts = int(datetime.datetime(int(y) + 1911, int(mo), int(dd), 12).timestamp())
            if u not in seen and ts >= cut and REL.search(t):
                seen[u] = {'t': t, 's': '衛生福利部', 'ts': ts, 'u': u, 'c': [k for k, pat in CAT if re.search(pat, t)] or ['政策補助']}
        time.sleep(1)
    items = sorted([v for v in seen.values() if v['ts'] >= cut], key=lambda v: -v['ts'])[:300]
    news = {'updated': int(time.time()), 'items': items, 'src': '衛生福利部新聞稿'}
    H = H[:i] + json.dumps(news, ensure_ascii=False).replace('</', '<\\/') + H[j:]
    print('新聞', len(items))
except Exception as e:
    print('新聞失敗，沿用舊資料：', e)

open('index.html', 'w', encoding='utf-8').write(H)
