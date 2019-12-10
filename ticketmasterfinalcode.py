import ticketpy
import requests
import json
import sqlite3
import os
import secrets
import matplotlib.pyplot as plt

CACHE_FNAME = 'tmaster.json'
try:
    cache_file = open(CACHE_FNAME, 'r')
    cache_contents = cache_file.read()
    CACHE_DICTION = json.loads(cache_contents)
    cache_file.close()
except:
    CACHE_DICTION = {}

def get_unique_key(url):
    return url

def make_requests_using_cache(url):
    unique_ident = get_unique_key(url)
    if unique_ident in CACHE_DICTION:
        return CACHE_DICTION[unique_ident]
    else:
        resp = requests.get(url)
        CACHE_DICTION[unique_ident] = resp.text
        dumped_json_cache = json.dumps(CACHE_DICTION)
        fw = open(CACHE_FNAME, 'w')
        fw.write(dumped_json_cache)
        fw.close()
        return CACHE_DICTION[unique_ident]


def get_events_from_city(conn, cur, city,limit=20):
    cur.execute('SELECT Page FROM Most_Recent_City_Call WHERE City = ?', [city])
    resp = cur.fetchall()
    if len(resp) == 0:
        page = 1
    else:
        page = resp[0][0]
    
    cur.execute('INSERT OR REPLACE INTO Most_Recent_City_Call(city, page)  values (?, ?)', [city, (page+1)])
    conn.commit()

    api_key = secrets.api_key
    base_url = "https://app.ticketmaster.com/discovery/v2/events.json?apikey={}&city={}&size={}&page={}".format(api_key,city,limit, page)
#   params = {"apikey": api_key, "city": city}


    initial = make_requests_using_cache(base_url)
    data = json.loads(initial)
    first= data["_embedded"]["events"]
#   print(data["_embedded"]['events'][0]['_embedded']['venues'][0]['name'])
    lst=[]
    for x in first:
        name=x["name"]
        genre = x["classifications"][0]['genre']['name']
        date=x['dates']['start']['localDate']
        v=x['_embedded']['venues']
        for i in v:
            city = i['city']['name']
            venue= i['name']
        cur.execute('INSERT INTO Event_Counts(Genre, Count) VALUES (?, 1) ON CONFLICT(Genre) DO UPDATE SET Count = Count + 1', [genre])
        conn.commit()
        lst.append((name, venue, city, genre, date))
    #change order?
    #add date if i want it back
#print(lst)
    return lst

#get_events_from_city("new york")



def get_desired_city():
    desired_city = ''
    desired_city = input('What city do you want to find upcoming events in? ')
        
    return desired_city

def create_SQLite_objects():
    try:
        path = os.path.dirname(os.path.abspath(__file__))
        conn = sqlite3.connect(path +'/'+'TICKETMASTER.sqlite')
        cur = conn.cursor()
        return cur, conn
    except:
        print("Could not connect")


def create_SQLite_venue_database(data, cur, conn):
    

    #might need to take out 3 lines above or edit to add new items if same city called
    #ask how to get the next twenty, not duplicates of the same 20
    
    cur.execute('CREATE TABLE IF NOT EXISTS Most_Popular_Genre(Name TEXT, Venue TEXT, City TEXT, Genre TEXT, Date TEXT, FOREIGN KEY (Genre) REFERENCES Event_Counts(Genre)) ')     
    for venue in data:
        cur.execute('INSERT INTO Most_Popular_Genre(Name, Venue, City, Genre, Date) VALUES (?, ?, ?, ?, ?)', (venue[0], venue[1], venue[2], venue[3], venue[4])) 
    conn.commit() 
    cur.close() 

def create_SQLite_pages_tables(conn, cur):
    cur.execute('CREATE TABLE IF NOT EXISTS Most_Recent_City_Call(City TEXT PRIMARY KEY, Page INTEGER)')
    conn.commit()
    cur.execute('CREATE TABLE IF NOT EXISTS Event_Counts(Genre NUMBER PRIMARY KEY, Count INTEGER)')
    conn.commit()

def select_data_from_SQLite_table(cur,conn):
    cur.execute("SELECT Name, Venue, City, Genre, Date FROM Most_Popular_Genre")
    list_venues = []
    for row in cur:
        list_venues.append(row)
    print(list_venues)

#make interactive-- if user input is weather, call on weather API?

def create_malplot():
    path = os.path.dirname(os.path.abspath(__file__))
    conn = sqlite3.connect(path +'/'+'TICKETMASTER.sqlite')
    cur = conn.cursor()    
    genres = cur.execute('SELECT DISTINCT E.Genre,City,Count from Most_Popular_Genre M JOIN Event_Counts E ON E.Genre = M.Genre')
    #do i need distinct?
    #genres=[g[0] for g in genres]
    generes_dicontary = {}
    city = None
    for row in genres:
        genre = row[0]
        count = row[2]
        city = row[1]
        if genre not in generes_dicontary:
            generes_dicontary[genre] = count
    
    #with open(filename, 'w') as f:
    #    [f.write('{0},{1}\n'.format(key, value)) for key, value in genres.items()]
    #print(genres)
    #make dictionary instead?
    #might need to fix underneath-- ask tori
    sizes = generes_dicontary.values()
    labels = generes_dicontary.keys()
    #make into dictionary and then make into list?
    #how do i make sizes based on data
    colors = ['#ff9999','#66b3ff','#99ff99','#ffcc99']
    #explode = (0, 0.1, 0, 0)  # only "explode" the 2nd slice (i.e. 'Hogs')
    #how do i make explode based on largest portion from data?
    fig1, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors = colors, shadow=True, startangle=90)   
    ax1.set_title('Most Popular Genre for Upcoming Events in {}'.format(city) , fontname= 'Times New Roman', fontsize=20, color='Black')
    fig1.savefig("genres_pie")
    #would i do plt instead of fig 1 to update what image is saved?-- does it even need to update?
    #how do i save to the same folder?
    #add explode back in above when figure it out
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.show()

    
def drop_cities(conn, cur):
    statement = "DROP TABLE IF EXISTS Most_Recent_City_Call"
    cur.execute(statement)
    conn.commit()
    statement = "DROP TABLE IF EXISTS Most_Popular_Genre;"
    cur.execute(statement)
    conn.commit()
    statement = "DROP TABLE IF EXISTS Event_Counts;"
    cur.execute(statement)
    conn.commit()

def main():
    
    cur, conn = create_SQLite_objects()
    city = get_desired_city()
    cur.execute('SELECT City FROM Most_Recent_City_Call')
    data = cur.fetchall()
    if len(data) > 0 and data[0][0] != city:
        drop_cities(conn, cur)
        


    create_SQLite_pages_tables(conn, cur)
    size=20
    data = get_events_from_city(conn, cur, city,size)
    sql_objects = create_SQLite_objects()
    create_SQLite_venue_database(data,sql_objects[0],sql_objects[1])
    create_malplot()

    # statement = "DROP TABLE IF EXISTS Most_Recent_City_Call"
    # cur.execute(statement)
    # conn.commit()


if __name__ == "__main__":
    main()