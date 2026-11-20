from sys import argv
import requests
import json
from time import strftime

class Dtek:
    """structurizes data from html"""
    def __init__(self, session, schedule):
        self.session = session

        self.schedule = schedule
        self.present = None
        self.streets = None
        self.fact = None
        self.cekText = None
        self.datateasm = None

        self.token = None
        self.currentWeekDayIndex = 0
        self.showCurOutage = False
        self.showCurSchedule = False
        self.showTableSchedule = False
        self.showTablePlan = False
        self.showTableFact = False
        self.showUserGroup = False

        for line in self.schedule[::-1]:
            if 'DisconSchedule.preset' in line:
                self.present = json.loads(line.lstrip('DisconSchedule.preset = '))
            if '<script>DisconSchedule.streets = ' in line:
                self.streets = json.loads(line.lstrip('<script>DisconSchedule.streets = '))
            if 'DisconSchedule.fact = ' in line:
                scriptEnd = line.find('</script>')
                if scriptEnd > 0:
                    line = line[:scriptEnd]
                self.fact = json.loads(line.lstrip('DisconSchedule.fact = '))


            if 'DisconSchedule.currentWeekDayIndex = ' in line:
                self.currentWeekDayIndex = int(line.lstrip('DisconSchedule.currentWeekDayIndex = '))

            if 'DisconSchedule.showCurOutage = ' in line:
                self.showCurOutage = {'true': True, 'false': False}[line.split(" = ")[-1].strip()]
            if 'DisconSchedule.showCurSchedule = ' in line:
                self.showCurSchedule = {'true': True, 'false': False}[line.split(" = ")[-1].strip()]
            if 'DisconSchedule.showTableSchedule = ' in line:
                self.showTableSchedule = {'true': True, 'false': False}[line.split(" = ")[-1].strip()]
            if 'DisconSchedule.showTablePlan = ' in line:
                self.showTablePlan = {'true': True, 'false': False}[line.split(" = ")[-1].strip()]
            if 'DisconSchedule.showTableFact = ' in line:
                self.showTableFact = {'true': True, 'false': False}[line.split(" = ")[-1].strip()]
            if 'DisconSchedule.showUserGroup = ' in line:
                self.showCurOutage = {'true': True, 'false': False}[line.split(" = ")[-1].strip()]
            if  '<script src="/src/js/static/nForm.check-application.js"></script>' in line:
                break

        for line in self.schedule:
            if '<meta name="csrf-token" content=' in line:
                self.token = line.lstrip('<meta name="csrf-token" content="').rstrip('">\n')
            if '<p><span data-teams="true">' in line:
                self.datateams = line.lstrip('<p><span data-teams="true">').rstrip('</span></p>')
                self.datateams = '\033[37m' + self.datateams.replace('<strong>', '\033[1m\033[39m').replace('</strong>', '\033[37m') + '\033[0m'

class Session:
    def __init__(self):
        self.s = requests.Session()
        self.r = None

    def get(self, url, headers=None):
        if headers:
            self.r = self.s.get(url, headers=headers)
        else:
            self.r = self.s.get(url)

    def post(self, url, data=None):
        if data:
            self.r = self.s.post(url, data=data)

def get_schedule_today(dtek:Dtek, group:str):

    group = "GPV" + group
    schedule_bar = ""
    for hour, value in dtek.fact["data"][str(dtek.fact["today"])][group].items():
        #print(f"{hour.zfill(2)}:00 = {value}")
        clrs = {"yes": "\33[93m",
                "no": "\33[34m",
                "maybe": "\33[90m",
                "first": "½",
                "second": "²",}
        print(f"{clrs[value]}{hour.zfill(2)}:00", end='\033[0m, ')
    print('')


def get_group(dtek:Dtek, city:str, address:str, house:str) -> str:
    group = 'unknown'
    found = False
    for cities in range(len(dtek.streets)):
        for k, v in dtek.streets.items():
            if city.lower() in k.lower():
                city = k
                for st in range(len(dtek.streets[k])):
                    if address.lower() in dtek.streets[k][st].lower():
                        address = dtek.streets[k][st]
                        found = True
                        break
        if not found:
            raise Exception(f"Can't find city {city} or address {address}")


    data = {'method': "getHomeNum",
                'data[0][name]': "city",
                'data[0][value]': city.encode('utf-8'),
                'data[1][name]': "street",
                'data[1][value]': address.encode('utf-8'),
                'data[2][name]': "updateFact",
                'data[2][value]': strftime("%d.%m.%Y %H:%M")}

    headers = {'X-CSRF-Token': dtek.token,
               'Content-Type': "application/x-www-form-urlencoded; charset=UTF-8"}

    req = requests.Request('GET', "https://www.dtek-oem.com.ua/ua/ajax", data=data, headers=headers)
    prepped = dtek.session.s.prepare_request(req)
    resp = dtek.session.s.send(prepped)

    resp = json.loads(resp.text)

    for i in range(len(resp["data"])):
        for k, v in resp["data"].items():
            if house.lower() == k.lower():
                house = k
                group = resp["data"][house]["sub_type_reason"][0].lstrip('GPV')
                break
        if group == 'unknown':
            for k, v in resp["data"].items():
                if house in k:
                    house = k
                    group = resp["data"][house]["sub_type_reason"][0].lstrip('GPV')
                    break
        if group == 'unknown':
            raise Exception(f"Can't find house {house}")
    print((city, address, house, group))

def main():
    """args python3 dtek.py -schedule [1.1] (for getting schedule)"""
    """args python3 dtek.py -get-group [city] [address] [house number] (for getting your group)"""
    s = requests.Session()
    html = s.get("https://www.dtek-oem.com.ua/ua/shutdowns")

    with open('shutdowns.html', 'w') as f:
        f.write(html.text)

    dtek = Dtek(s, html.text.split('\n'))

    s.headers.update({"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                      "X-CSRF-Token": dtek.token})
    r = s.get("https://www.dtek-oem.com.ua/ua/ajax", data={'method': "getCekText"})
    dtek.cekText = r.json()["cekText"]

    for arg in range(len(argv)):

        if argv[arg] == "-schedule":
            group = argv[arg+1]
            try:
                _ = float(group)
            except:
                raise Exception(f"{group} can't be a group!")
            get_schedule_today(dtek, group=group)

        if argv[arg] == "-get-group":
            city, address, house = argv[arg+1:arg+4]
            group = get_group(dtek, city, address, house)

        if argv[arg] == "--help":
            print("To get your group: dtek-cli.py -get-group [city] [street] [house]\nExample input: Одес Трансп 1\nIf it found you will get your corrected address and group.")
            print("To get shutdown table for today: dtek-cli.py -schedule [your group]")
            print("Current state message: --message")
            print("Your SCRF-Token: --token")
            print("\n\033[1mExample: python3 dtek-cli.py --token --message -schedule 1.1")
        if argv[arg] == "--message":
            print(dtek.datateams)#print(dtek.cekText)

        if argv[arg] == "--token":
            print(dtek.token)

    #get_group(dtek, "Одеса", "Транспо", "1")
    #get_schedule_today(dtek, group='3.1')
    #print(get_group())


if __name__ == '__main__':
    main()
