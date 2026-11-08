import re, requests, os
S=requests.Session(); S.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://www.tuneps.tn/portail/offres"}); V=os.environ["CA"]
B="https://www.tuneps.tn"
t=S.get(B+"/main.js",verify=V,timeout=120).text
for k in ['baseGedShop','.baseGed ','baseGed =','apiGed','gedShop','GED_SHOP','urlGed']:
    for m in list(re.finditer(re.escape(k),t))[:3]:
        print("##",k,"::",re.sub(r"\s+"," ",t[max(0,m.start()-150):m.start()+250])); print()
for k in re.findall(r'["\'`](/?api2?/ged[A-Za-z_-]*/?)["\'`]',t)[:20]: print("##BASE",k)
for k in set(re.findall(r'["\'`]([^"\'`\s]{0,30}ged[^"\'`\s]{0,30})["\'`]',t, re.I)): 
    if '/' in k: print("##CAND",k)
