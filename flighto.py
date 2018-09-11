import requests

url = 'https://www.hipmunk.com/api/flights/v3/load_search_first'

payload = {
    'date0': '11/22/2018',
    'from0': 'LHR',
    'to0': 'JFK',
}

headers = {
    'accept':'application/json, text/javascript, */*; q=0.01',
    'accept-encoding':'gzip, deflate, br',
    'accept-language':'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
    'authority':'www.hipmunk.com',
    'content-type':'application/x-www-form-urlencoded; charset=UTF-8',
    # 'cookie'
    'origin':'https://www.hipmunk.com',
    'referer':'https://www.hipmunk.com/flights',
    'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36',
    # 'x-csrf-token'
    'x-hipmunk-api':'true',
    'x-requested-with':'XMLHttpRequest',
}

try:
    r = requests.post(url, headers=headers, data=payload)
except:
    print('failed to request', sys.exc_info()[0])

print('done requesting')

results = r.json()
routings = results['routings']
legs = results['legs']
itins = results['itins'].values()

for itin in itins:
    routing_iden = itin['routing_idens'][0]
    my_routing = routings[routing_iden]
    leg_idens = my_routing['leg_idens']

    print('price', itin['price'])
    for leg_iden in leg_idens:
        leg = legs[leg_iden]
        from_code = leg['from_code']
        to_code = leg['to_code']
        depart = leg['depart']
        arrive = leg['arrive']
        flight = leg['operating_num'] or leg['marketing_num']
        airline, flight_no = flight
        print(leg)

    break
