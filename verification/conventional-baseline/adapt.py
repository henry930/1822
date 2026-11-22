import sys,re,os
D=sys.argv[1]; E=D+'/backend/app/engine'
AL={'bidding':[('_face_value','face_value')],'certificates':[('certificate_limit','cert_limit'),('certificate_count','cert_count')],
'turn_order':[('compute_operating_order','operating_order'),('next_player_order','compute_stock_round_order')],
'round_manager':[('start_operating_round_set','start_operating_round')],'scoring':[('final_wealth','player_wealth'),('final_standings','final_ranking')]}
for m,l in AL.items():
    p=f'{E}/{m}.py'; s=open(p).read()
    for a,t in l:
        if not re.search(r'^(def|class)\s+'+a+r'\b|^'+a+r'\s*=',s,re.M) and re.search(r'^(def|class)\s+'+t+r'\b|^'+t+r'\s*=',s,re.M):
            s+=f"\n{a} = {t}\n"; print(D,'alias',m,a,'=',t)
    open(p,'w').write(s)
