from mwrogue.auth_credentials import AuthCredentials
from mwrogue.esports_client import EsportsClient
from mwrogue.wiki_time_parser import time_from_str

credentials = AuthCredentials(user_file='me')

site = EsportsClient('lol', credentials=credentials)

# for ns in site.namespaces:
#     print(ns.name)

assert site.query_bayes_id('ESPORTSTMNT01_2200321')['Event'] == 'LCK 2021 Summer Playoffs'

assert site.cache.get_disambiguated_player_from_event('European Masters/2021 Season/Spring Play-In', 'G2 Arctic',
                                                      'Koldo') == 'Koldo'

assert site.cache.get_disambiguated_player_from_event(
    'Claro Stars League/2021 Season/Opening Season', 'Luxor Gaming', 'Zeldris') == 'Zeldris (Christian Ticlavilca)'

assert site.cache.get_disambiguated_player_from_event(
    'El_Nexo/2020_Season/Split_1_Playoffs', 'Movistar Riders Academy', 'Marky'
) == 'Marky (Pedro José Serrano)'

# check fallback to tournament rosters short
assert site.cache.get_team_from_event_tricode('2014 Season World Championship', 'NWS') == 'NaJin White Shield'

assert site.cache.get_team_from_event_tricode('Worlds 2019 Main Event', 'SKT') == 'SK Telecom T1'

assert site.cache.get_disambiguated_player_from_event(
    'Worlds 2019 Main Event', 'Splyce', 'Duke') == 'Duke (Hadrien Forestier)'

assert time_from_str("2020-03-27T16:49:18+00:00").dst == 'spring'

# check special character
assert site.cache.get_disambiguated_player_from_event(
    'Belgian League 2020 Summer', 'Aethra Esports', 'Tuomarí') == 'Tuomarí'

assert sum(1 for _ in site.data_pages('LDL 2020 Summer')) == 11

# check a team without a teamnames entry
assert site.cache.get_team_from_event_tricode('Ultraliga Season 5 Promotion', 'Soon') == 'soon to be named'

# check a low-priority redirect player
assert site.cache.get_disambiguated_player_from_event(
    'LCS 2020 Summer', 'FLY', 'Solo') == 'Solo (Colin Earnest)'

# check tournaments to script
assert "Music X Esports: Hyperplay 2018" in site.tournaments_to_skip('mhtowinners')

# Check game data and timeline from game id result (Should be tuple of 2 elements => (data, timeline))
assert len(site.get_data_and_timeline_from_gameid("LEC/2022 Season/Spring Season_Week 8_15_1")) == 2

# Check cargo teamnames
assert site.cache.get_cargo_teamname("isg", "Link") == "Isurus"

# Check if teamnames inputs is actually a list and we split correctly
assert isinstance(site.cache.get_cargo_teamname("fnc", "Inputs"), list)

# Check if cargo teamnames cache was populated
assert site.cache.cargo_teamnames_cache
