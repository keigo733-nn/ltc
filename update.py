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

# ---------- 2. 長照新聞（中央部會＋北北基桃市府，只存標題與連結） ----------
import http.cookiejar, urllib.parse
SRC = [  # (名稱, 網址, 類別, 頁數參數)
    ('衛生福利部', 'https://www.mohw.gov.tw/lp-16-1-{p}-20.html', '中央', 5),
    ('衛生福利部', 'https://www.mohw.gov.tw/lp-17-1-{p}-20.html', '中央', 2),
    ('行政院', 'https://www.ey.gov.tw/Page/6485009ABEC1CB9C?page={p}', '中央', 3),
    ('勞動部', 'https://www.mol.gov.tw/1607/1632/1633/', '中央', 1),
    ('臺北市政府', 'https://www.gov.taipei/News.aspx?n=F0DDAF49B89E9413&sms=72544237BBE4C5F6&PageSize=200', '臺北', 1),
    ('臺北市社會局', 'https://dosw.gov.taipei/News.aspx?n=6CA16D3397A7A302&sms=72544237BBE4C5F6&PageSize=100', '臺北', 1),
    ('臺北市衛生局', 'https://health.gov.taipei/News.aspx?n=BB5A41BA1E6CA260&sms=72544237BBE4C5F6&PageSize=100', '臺北', 1),
    ('新北市政府', 'https://www.ntpc.gov.tw/ch/home.jsp?id=e8ca970cde5c00e1&page={p}', '新北', 6),
    ('桃園市政府', 'https://www.tycg.gov.tw/NewsPage.aspx?n=10&sms=7885&PageSize=100', '桃園', 1),
    ('桃園市社會局', 'https://sab.tycg.gov.tw/News.aspx?n=7303&sms=11860&PageSize=100', '桃園', 1),
    ('桃園市衛生局', 'https://dph.tycg.gov.tw/News.aspx?n=4218&sms=10120&PageSize=100', '桃園', 1),
    ('基隆市政府', 'https://www.klcg.gov.tw/tw/klcg1/3168.html', '基隆', 1),
]
REL = re.compile(r'長照|長期照顧|照顧服務|照護|安養|養護|護理之家|失智|失能|看護|喘息|日照|老人|長者|長輩|高齡|銀髮|身障|身心障礙|輔具|臥床|住宿式|1966|照顧者|銀光|敬老|重陽')
NOT = re.compile(r'兒童|幼兒|托嬰|育兒|學童|街貓|動保|寵物|毛孩|節電|節能')
CAT = [('政策補助', r'補助|給付|津貼|3\.0|新制|方案|預算|費用|免費|減免|加碼'), ('機構與稽查', r'機構|稽查|評鑑|裁罰|查核|安全|火|消防|違規'),
       ('失智與照顧', r'失智|照顧者|喘息|日照|看護|照顧|失能')]
DATE = re.compile(r'(20\d\d|1[01]\d)\s*[-/.年]\s*(\d{1,2})\s*[-/.月]\s*(\d{1,2})')
cj = http.cookiejar.CookieJar(); OP = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
OP.addheaders = [('User-Agent', 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/120 Safari/537.36'), ('Accept-Language', 'zh-TW,zh')]
def fetch(u):
    for k in range(3):
        try: return OP.open(u, timeout=40).read().decode('utf-8', 'ignore')
        except Exception as e: err = e; time.sleep(3)
    raise err
def extract(u, x):
    out = []
    for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', x, re.S):
        h = re.search(r'href="([^"#][^"]*)"', m.group(1))
        if not h: continue
        t = re.search(r'title="([^"]{8,})"', m.group(1))
        text = html.unescape(re.sub(r'<[^>]+>|\s+', ' ', m.group(2))).strip()
        title = re.sub(r'\(另開新視窗\)|（另開新視窗）', '', html.unescape(t.group(1)) if t else text).strip()
        if len(title) < 10 or len(title) > 120: continue
        d = DATE.search(re.sub(r'<[^>]+>', ' ', x[m.end():m.end() + 500])) or DATE.search(re.sub(r'<[^>]+>', ' ', m.group(2)))
        if not d: continue
        y = int(d.group(1)); y = y + 1911 if y < 1000 else y
        try: ts = int(datetime.datetime(y, int(d.group(2)), int(d.group(3)), 12).timestamp())
        except ValueError: continue
        out.append((title, urllib.parse.urljoin(u, html.unescape(h.group(1))), ts))
    return out
try:
    i, j = js_block('let NEWS=', ';let NCAT=')
    news = json.loads(H[i:j].replace('<\\/', '</'))
    seen = {x['u']: x for x in news.get('items', [])}
    titles = {re.sub(r'\W', '', x['t'])[:24] for x in seen.values()}
    cut = time.time() - 125 * 86400; got = {}
    for name, url, area, pages in SRC:
        n = 0
        for p in range(1, pages + 1):
            try: L = extract(url, fetch(url.format(p=p)))
            except Exception as e: print('  失敗', name, e); break
            for t, u, ts in L:
                k = re.sub(r'\W', '', t)[:24]
                if u in seen or k in titles or ts < cut or ts > time.time() + 86400 or not REL.search(t) or NOT.search(t): continue
                c = [kk for kk, pat in CAT if re.search(pat, t)] or ['政策補助']
                if area != '中央': c.append('北北基桃')
                seen[u] = {'t': t, 's': name, 'ts': ts, 'u': u, 'c': c, 'a': area}; titles.add(k); n += 1
            time.sleep(1)
        got[name] = got.get(name, 0) + n
    items = sorted([v for v in seen.values() if v['ts'] >= cut], key=lambda v: -v['ts'])[:400]
    news = {'updated': int(time.time()), 'items': items, 'src': '中央部會與北北基桃市政府新聞稿'}
    H = H[:i] + json.dumps(news, ensure_ascii=False).replace('</', '<\\/') + H[j:]
    print('新聞', len(items), got)
except Exception as e:
    print('新聞失敗，沿用舊資料：', e)

open('index.html', 'w', encoding='utf-8').write(H)
