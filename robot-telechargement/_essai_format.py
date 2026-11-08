import re, requests, os
S=requests.Session(); S.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://www.tuneps.tn/portail/offres"}); V=os.environ["CA"]
B="https://www.tuneps.tn"
t=S.get(B+"/main.js",verify=V,timeout=120).text
for k in ['downloadFileShop(','downloadFile(','downloadFileWithFileLoc(','downloadEdoc','baseGed =','baseGed=','downloadFileLocally(']:
    ms=list(re.finditer(re.escape(k),t))
    for m in ms[-3:]:
        print("##",k,"::",re.sub(r"\s+"," ",t[max(0,m.start()-80):m.start()+450])); print()
