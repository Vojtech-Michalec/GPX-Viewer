import folium
import gpxpy
import os
import json
from datetime import datetime
from collections import defaultdict
from dotenv import load_dotenv
from ftplib import FTP

# Funkce pro načtení GPX souborů a filtrování podle data
def load_gpx_files(directory):
    gpx_files = []
    for filename in os.listdir(directory):
        if filename.endswith('.gpx'):
            date_str, title = filename.split(' - ', 1)
            date_str = date_str.strip()
            file_date = datetime.strptime(date_str, '%Y%m%d')
            gpx_files.append((os.path.join(directory, filename), file_date, title.strip('.gpx')))
    return gpx_files

# najít střed trasy
def calculate_center(points):
    if not points:
        return None
    latitudes = [point[0] for point in points]
    longitudes = [point[1] for point in points]
    center_lat = sum(latitudes) / len(latitudes)
    center_lon = sum(longitudes) / len(longitudes)
    return (center_lat, center_lon)

# GPX na mapu
def add_gpx_to_map(gpx_files, map_obj):
    routes = []
    for gpx_file, file_date, title in gpx_files:
        with open(gpx_file, 'r') as f:
            gpx = gpxpy.parse(f)
            for track in gpx.tracks:
                for segment in track.segments:
                    points = [(point.latitude, point.longitude) for point in segment.points]
                    center = calculate_center(points)
                    color = '#000000'
                    if file_date.year == 2024:
                        color = '#FF0000'
                    elif file_date.year == 2023:
                        color = '#0000FF'
                    elif file_date.year == 2025:
                        color = '#008000'
                    # Přidání polyline na mapu
                    folium.PolyLine(
                        points,
                        color=color,
                        popup=f"<b>{title}</b><br>{file_date.strftime('%d.%m.%Y')}",
                    ).add_to(map_obj)
                    # Uložení do seznamu
                    routes.append({
                        'points': points,
                        'title': title,
                        'date': file_date.strftime('%d.%m.%Y'),
                        'center': center,
                        'year': file_date.year,
                        'color': color
                    })
    return routes

def group_routes(routes):
    grouped = defaultdict(list)

    # Skupinování tras podle místa a dat
    for route in routes:
        place = route["title"]
        # Ošetření datumu s možností rozmezí
        date_str = route["date"]
        dates = []
        if '–' in date_str:  # Zkontroluj, zda je v datu rozmezí
            start_date_str, end_date_str = date_str.split('–')
            start_date = datetime.strptime(start_date_str.strip(), '%d.%m.%Y')
            end_date = datetime.strptime(end_date_str.strip(), '%d.%m.%Y')
            dates.append(start_date)
            dates.append(end_date)
        else:
            date = datetime.strptime(date_str, '%d.%m.%Y')
            dates.append(date)

        for date in dates:
            grouped[place].append(date)

    # Příprava seznamu pro zobrazení
    display_routes = []
    for place, dates in grouped.items():
        dates.sort()  # Řazení dat
        # Skupinování po sobě jdoucích dat
        start_date = dates[0]
        end_date = start_date

        for current_date in dates[1:]:
            if (current_date - end_date).days == 1:  # Kontrola, zda jsou data za sebou
                end_date = current_date
            else:
                if start_date == end_date:
                    display_routes.append({
                        "place": place,
                        "date": start_date.strftime('%d.%m.%Y')
                    })
                else:
                    display_routes.append({
                        "place": place,
                        "date": f"{start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}"
                    })
                start_date = current_date
                end_date = current_date

        # Přidání posledního rozsahu
        if start_date == end_date:
            display_routes.append({
                "place": place,
                "date": start_date.strftime('%d.%m.%Y')
            })
        else:
            display_routes.append({
                "place": place,
                "date": f"{start_date.strftime('%d.%m.%Y')} – {end_date.strftime('%d.%m.%Y')}"
            })

    # Řazení konečného seznamu podle data
    display_routes.sort(key=lambda x: datetime.strptime(x['date'].split(' – ')[-1], '%d.%m.%Y'))

    return display_routes


def save_routes_to_js(routes):
    seen_places = set()  # Množina pro uchování již přidaných názvů
    data_for_js = []

    for route in routes:
        place = route["title"]
        if place not in seen_places:  # Kontrola, zda je jméno již přidáno
            data_for_js.append({"place": place, "date": route["date"]})
            seen_places.add(place)  # Přidání názvu do množiny

    return data_for_js

# Vytvoření mapy
map_obj = folium.Map(location=[50.209, 15.832], zoom_start=13, control_scale=True)

# Načtení a přidání GPX souborů na mapu
gpx_files = load_gpx_files('gpx')
routes = add_gpx_to_map(gpx_files, map_obj)
data_for_js = save_routes_to_js(routes)
data_routes = group_routes(routes)

# HTML a CSS pro vyhledávací pole, panel s roky a mapu
content = f"""<!DOCTYPE html>
<html lang="cs-CZ">
<head>
    <meta http-equiv="content-type" content="text/html; charset=UTF-8" />
    
        <script>
            L_NO_TOUCH = false;
            L_DISABLE_3D = false;
        </script>
    
    <style>html, body {{width: 100%;height: 100%;margin: 0;padding: 0;}}</style>
    <style>#map {{position:absolute;top:0;bottom:0;right:0;left:0;}}</style>
    <script src="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.js"></script>
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.js"></script>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/leaflet@1.9.3/dist/leaflet.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.2/dist/css/bootstrap.min.css"/>
    <link rel="stylesheet" href="https://netdna.bootstrapcdn.com/bootstrap/3.0.0/css/bootstrap-glyphicons.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.2.0/css/all.min.css"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/Leaflet.awesome-markers/2.0.2/leaflet.awesome-markers.css"/>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/python-visualization/folium/folium/templates/leaflet.awesome.rotate.min.css"/>
    
            <meta name="viewport" content="width=device-width,
                initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
<title>TOM Hraboši - výpravy</title>
        
</head>
<style>
    body, html {{             
            margin: 0;
            padding: 0;
            overflow: hidden;
            height: 100%;
            display: flex; }}
    #map {{ height: 100vh; width: 100vw; transition: margin-left 0.3s; width: calc(100%);}}
    .popup-content {{
        font-size: 14px;
    }}
    .search-container {{
        position: absolute;
        top: 18px;
        right: 25px;
        z-index: 1000;
        display: flex;
        align-items: center;
    }}
    .search-input {{
        width: 400px;
        padding: 20px;
        border-radius: 36px;
        border: 2px solid #122F35;
        outline: none;
        font-size: 16px;
        z-index: 999;
    }}
    .search-icon {{
        position: absolute;
        top: 7px;
        right: 7px;
        width: 52px;
        height: 52px;
        border-radius: 50%;
        background-color: #122F35;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 1000;
    }}
    .search-icon img {{
        width: 25px;
        height: 25px;
    }}
    .circle-icon {{
        position: absolute;
        top: 18px;
        right: 450px;
        width: 65px;
        height: 65px;
        border-radius: 50%;
        background-color: #fff;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        z-index: 1000;
    }}
    .circle-icon img {{
        width: 60px;
        height: 60px;
    }}
    .category-button {{
        position: absolute;
        bottom: 18px;
        right: 25px;
        z-index: 1000;
        padding: 10px 20px;
        background-color: #122F35;
        color: #fff;
        border: none;
        border-radius: 36px;
        cursor: pointer;
        font-size: 16px;
    }}
    .category-panel {{
        display: none;
        position: absolute;
        bottom: 80px;
        right: 25px;
        background-color: #fff;
        border: 1px solid #ccc;
        border-radius: 12px;
        padding: 10px;
        z-index: 1000;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .category-panel label {{
        display: block;
        padding: 5px;
    }}
    .category-panel input[type="checkbox"] {{
        margin-right: 10px;
    }}
    .suggestions {{
        position: absolute;
        left: 25px;
        top: 100%; 
        margin-top: -1px; 
        z-index: 998;
        background-color: rgba(255, 255, 255, 0);
        border: none;
        max-width: 410px;
        max-height: 200px; 
        overflow-y: auto;
        border-radius: 5px; 
    }}
    .suggestions div {{
        padding: 5px;
        width: 340px;
        background-color: rgb(255, 255, 255);
        border: 1px solid #ddd;
        cursor: pointer;
    }}
    .suggestions div:hover {{
        background-color: #f0f0f0;
    }}
    .route-button {{
    position: fixed;
    bottom: 20px;
    left: 20px;
    width: 45px;
    height: 45px;
    border-radius: 50%;
    background-color: #122F35;
    background-size: cover;
    background-position: center;
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
    border: none;
    cursor: pointer;
    z-index: 1000;
    display: flex;
    justify-content: center;
    align-items: center;
    transition: margin-left 0.3s;
}}

.hamburger {{
    width: 15px;
    height: 15px;
    position: relative;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    align-items: center;
}}


.hamburger .bar {{
    width: 100%;
    height: 3px;
    background-color: white;
    border-radius: 4px;
    transition: all 0.4s ease-in-out;
}}

.bar1 {{
    top: 0; 
}}

.bar2 {{
    top: 6px; 
}}

.bar3 {{
    bottom: 0; 
}}

.route-panel {{
    position: absolute;
    top: 0;
    left: -300px; 
    width: 300px;
    height: 100%;
    background-color: #fff;
    z-index: 1000;
    overflow-y: auto;
    transition: left 0.3s; 
}}
.route-panel div {{
    padding: 5px;
    background-color: rgb(255, 255, 255);
    cursor: pointer;
    position: relative;
}}
.route-panel div:hover {{
    background-color: #f0f0f0;
}}
.route-panel div::after {{
    content: "";
    display: block;
    width: 95%; 
    height: 1px; 
    background-color: #ccc;
    margin: 5px auto 0; 
}}
    @media only screen and (max-width: 768px) {{
        #map {{ height: 100vh; width: 100vw; width: calc(100%);}}
        .search-container {{
            top: 10px; 
            right: 10px; 
        }}

        .search-input {{
            width: 100%; 
            padding: 15px; 
            font-size: 14px; 
        }}

        .search-icon {{
            width: 40px; 
            height: 40px; 
        }}

        .category-button {{
            padding: 8px 16px; 
            font-size: 14px; 
        }}
        .circle-icon {{
            position: absolute;
            top: 10px;
            right: 250px;
            width: 50px;
            height: 50px;
            border-radius: 50%;
            background-color: #fff;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            z-index: 1000;
        }}
        .circle-icon img {{
            width: 45px;
            height: 45px;
        }}
        .suggestions {{
            position: absolute;
            left: 0; 
            top: 100%; 
            z-index: 998;
            background-color: rgba(255, 255, 255, 0);
            border: none;
            width: 100%; 
            max-width: none; 
            max-height: 200px; 
            overflow-y: auto;
            border-radius: 5px; 
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0); 
        }}
        .suggestions div {{
            padding: 5px;
            width: 100%;
            background-color: rgb(255, 255, 255);
            border: 1px solid #ddd;
            cursor: pointer;
        }}
        .route-panel {{
        padding: 2%;
        left: 0; 
        top: 100%; 
        width: 100%; 
        max-width: none; 
        height: 85%; 
        border-radius: 20px 20px 0 0;
        border: 4px solid #122F35; 
        border-bottom: none;
        transition: Top 0.3s; 
        z-index: 1010;
    }}
    .route-button {{
        bottom: 2%;
        transition: Bottom 0.3s;
        z-index: 1011; 
    }}
    .category-button {{
        bottom: 2%;
    }}
    .route-panel div:hover {{
    background-color: #fff;
}}
    }}
</style>
<div class="circle-icon" onclick="window.location.href='https://hrabosi.tomici.cz/'" title="Přejít na webové stránky">
    <img src="obrazky/hrabos.png" alt="Hrabos">
</div>
<div id="map"></div>
<div class="search-container">
    <input type="text" id="searchBar" class="search-input" placeholder="Vyhledat výpravu..." onkeyup="showSuggestions()">
    <div class="search-icon" onclick="findLocation()" title="Vyhledat">
        <img src="obrazky/lupa.png" alt="Lupa">
    </div>
    <div id="suggestions" class="suggestions"></div>
</div>
<button class="category-button" onclick="toggleCategoryPanel()">Roky</button>
<div class="category-panel" id="categoryPanel">
    <label><input type="checkbox" value="2024" onchange="filterRoutes()" checked>2024</label>
    <label><input type="checkbox" value="2023" onchange="filterRoutes()" checked>2023</label>
</div>
<div class="route-button" onclick="toggleRoutePanel()">    
    <div class="hamburger hamburger1">
    <span class="bar bar1"></span>
    <span class="bar bar2"></span>
    <span class="bar bar3"></span>
    </div>
</div>
<div class="route-panel" id="routePanel">
    <div id="routeList"></div>
</div>
<script>
const data = {json.dumps(data_for_js, ensure_ascii=False, indent=4)};

document.getElementById('searchBar').addEventListener('keydown', function(event) {{
    if (event.key === 'Enter') {{
        event.preventDefault();
        findLocation();}}}});
function showSuggestions() {{
    const input = document.getElementById("searchBar").value.trim();
    const suggestions = document.getElementById("suggestions");
    suggestions.innerHTML = "";

    if (input.length === 0) return; 

    
    const datePattern1 = /^\d{{2}}\.\d{{2}}\.\d{{4}}$/; 
    const datePattern2 = /^\d{{8}}$/;               
    let searchDate = input;

    if (datePattern2.test(input)) {{
      searchDate = `${{input.slice(6, 8)}}.${{input.slice(4, 6)}}.${{input.slice(0, 4)}}`;
    }}

    const filteredData = data.filter(item => {{
      return (
        item.place.toLowerCase().includes(input.toLowerCase()) ||  
        item.date.includes(searchDate)                             
      );
    }});


    filteredData.forEach(item => {{
      const suggestionDiv = document.createElement("div");
      suggestionDiv.textContent = item.place;
      suggestionDiv.onclick = () => {{ document.getElementById("searchBar").value = item.place; suggestions.innerHTML = ""; findLocation();}};
      suggestions.appendChild(suggestionDiv);
    }});
  }}
const routes = {json.dumps(data_routes)};

document.addEventListener('DOMContentLoaded', function() {{
    const panel = document.getElementById('routePanel');
    const map = document.getElementById('map');
    const button = document.querySelector('.route-button');
    const isMobile = window.innerWidth <= 768;

    window.toggleRoutePanel = function() {{
        if (isMobile) {{

        if (panel.style.top === '15%') {{
            panel.style.top = '100%';
            button.style.bottom = '2%';
        }} else {{
            panel.style.top = '15%';
            button.style.bottom = '82%';
        }}

        }}   else {{
            if (panel.style.left === '0px') {{
                panel.style.left = '-300px';
                map.style.marginLeft = '0';
                button.style.marginLeft = '0';
            }} else {{
                panel.style.left = '0px';
                map.style.marginLeft = '300px';
                button.style.marginLeft = '300px';
        }}
    }}
}}}});


document.addEventListener('DOMContentLoaded', function() {{
    const routeList = document.getElementById('routeList');

    routes.forEach(route => {{
        const routeItem = document.createElement('div');
        routeItem.innerHTML = `<b>${{route.place}}</b> <br>${{route.date}}`;
        

        routeItem.onclick = () => {{
            focusOnRoute(route.place);
            const isMobile = window.innerWidth <= 768; 
            if (isMobile) {{
                document.querySelector('.route-panel').style.top = '100%';
                document.querySelector('.route-button').style.bottom = '2%'; 
            }}
        }};
        
        routeList.appendChild(routeItem);
    }});
}});

function focusOnRoute(place) {{
    const searchBar = document.getElementById('searchBar');
    searchBar.value = place;
    findLocation();
}}
    document.addEventListener('DOMContentLoaded', function() {{
        const map = L.map('map').setView([50.209, 15.832], 13);
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            maxZoom: 18,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors | <a href="https://hrabosi.tomici.cz/">TOM Hraboši</a> 🐭',
        }}).addTo(map);
        const routes = {json.dumps(routes)};
        routes.forEach(function(route) {{
            L.polyline(route.points, {{color: route.color}}).addTo(map)
                .bindPopup("<div class='popup-content'><b>" + route.title + "</b><br>" + route.date + "</div>");
        }});

        L.marker([50.206875, 15.8349467], {{
            icon: L.icon({{
            iconUrl: 'obrazky/hrabos.png',
            iconSize: [30, 30]
            }})
        }}).addTo(map)
        .bindPopup("<div class='popup-content'><b>Hraboší doupě</b></div>");

        window.findLocation = function() {{
            const searchQuery = document.getElementById('searchBar').value.toLowerCase();
            const matchingRoutes = routes.filter(route =>
            route.title.toLowerCase() === searchQuery || route.date.includes(searchQuery)
            );
            if (matchingRoutes.length > 0) {{
                const latLngs = matchingRoutes.flatMap(route => route.points);
                const bounds = L.latLngBounds(latLngs);
                map.fitBounds(bounds);
                if (matchingRoutes.length === 1) {{
                    const popup = L.popup()
                        .setLatLng(matchingRoutes[0].center)
                        .setContent("<div class='popup-content'><b>" + matchingRoutes[0].title + "</b><br>" + matchingRoutes[0].date + "</div>")
                        .openOn(map);
                }}
            }} else {{
                alert("Trasa nenalezena.");
            }}
        }};

        window.toggleCategoryPanel = function() {{
            const panel = document.getElementById('categoryPanel');
            panel.style.display = panel.style.display === 'block' ? 'none' : 'block';
        }};

        window.filterRoutes = function() {{
            const checkboxes = document.querySelectorAll('.category-panel input[type="checkbox"]:checked');
            const selectedYears = Array.from(checkboxes).map(checkbox => parseInt(checkbox.value));
    }}


window.filterRoutes = function() {{
    const checkboxes = document.querySelectorAll('.category-panel input[type="checkbox"]:checked');
    const selectedYears = Array.from(checkboxes).map(checkbox => parseInt(checkbox.value));


    map.eachLayer(function(layer) {{
        if (layer instanceof L.Polyline || layer instanceof L.Marker) {{
            map.removeLayer(layer);
        }}
    }});


    const matchingRoutes = routes.filter(route => selectedYears.includes(route.year));
    matchingRoutes.forEach(function(route) {{
        L.polyline(route.points, {{color: route.color}}).addTo(map)
            .bindPopup("<div class='popup-content'><b>" + route.title + "</b><br>" + route.date + "</div>");
    }});

    L.marker([50.206875, 15.8349467], {{
        icon: L.icon({{
            iconUrl: 'obrazky/hrabos.png',
            iconSize: [30, 30]
        }})
    }}).addTo(map)
    .bindPopup("<div class='popup-content'><b>Hraboší doupě</b></div>");
}};
}});
</script>
"""

# Uložení upraveného HTML souboru
with open('mapa.html', 'w', encoding='utf-8') as file:
    file.write(content)

load_dotenv(dotenv_path='FTP.env')
ftp_password = os.getenv('FTP_PASSWORD')
ftp_user = os.getenv('FTP_USER')
ftp_host = os.getenv('FTP_HOST')
try:
    print("Připojování k serveru...")
    ftp = FTP(ftp_host)
    ftp.login(user= ftp_user, passwd= ftp_password)
    print("Připojení k serveru bylo úspěšné.")

    # Odeslání souboru do specifikované cesty na vzdáleném serveru
    local_file_path = 'mapa.html'
    remote_file_path = '/www/mapa.html'
    with open(local_file_path, 'rb') as file:
        ftp.storbinary(f'STOR {remote_file_path}', file)
    print(f"Soubor {local_file_path} byl úspěšně nahrán na {remote_file_path}.")

    # Zavření FTP spojení
    ftp.quit()
    print("Spojení bylo úspěšně uzavřeno.")
except Exception as e:
    print(f"Došlo k chybě: {e}")