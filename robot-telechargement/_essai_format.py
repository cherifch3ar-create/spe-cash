import re, requests, os
S=requests.Session(); S.headers.update({"User-Agent":"Mozilla/5.0","Referer":"https://www.tuneps.tn/portail/offres"}); V=os.environ["CA"]
B="https://www.tuneps.tn"
for page in ["/", "/portail/offres"]:
    try:
        h=S.get(B+page,verify=V,timeout=60); print("PAGE",page,h.status_code,len(h.text))
        srcs=re.findall(r'src="([^"]+\.js)"',h.text); print("JS",srcs)
        if srcs: break
    except Exception as e: print("ERR",page,e)
for s in srcs:
    u=s if s.startswith("http") else B+"/"+s.lstrip("/")
    try: t=S.get(u,verify=V,timeout=90).text
    except Exception as e: print("ERR",u,e); continue
    for k in ['downloadFile','downloadFromGed','noderef','nodeRef','fileLoc']:
        for m in list(re.finditer(k,t))[:3]:
            print("##",s,k,"::",re.sub(r"\s+"," ",t[max(0,m.start()-200):m.start()+300])); print()
R='d05a7692-e5be-413e-9134-3ce09acd5049;1.0'
for p,v in [("noderef",R),("noderef",R.split(";")[0]),("nodeRef",R),("noderef","workspace://SpacesStore/"+R)]:
    try:
        r=S.get(B+"/api2/ged/document/downloadFile",params={p:v},verify=V,timeout=60)
        print("===",p,v,r.status_code,r.headers.get("content-type"),len(r.content),r.content[:150])
    except Exception as e: print("ERR",p,e)
