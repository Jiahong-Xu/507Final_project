#################################
##### Name: Jiahong Xu      #####
##### Uniqname: jiahongx    #####
#################################

from bs4 import BeautifulSoup
import requests
import json
#import secrets # file that contains your API key
import time
import sqlite3 
import collections
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.express as px
import pandas as pd

################### code for accessing API and crawling and cache  ##################
OMDb_BASE_URL = "http://www.omdbapi.com/?apikey=ff9eafcd"
IMDb_URL = "http://www.imdb.com"
CACHE_FILE_NAME = "cache.jason"

def load_cache():
    try:
        cache_file = open(CACHE_FILE_NAME, 'r')
        cache_file_contents = cache_file.read()
        cache = json.loads(cache_file_contents)
        cache_file.close()
    except:
        cache = {}
    return cache

def save_cache(cache):
    cache_file = open(CACHE_FILE_NAME, 'w')
    contents_to_write = json.dumps(cache)
    cache_file.write(contents_to_write)
    cache_file.close()

CACHE_DICT = load_cache()

def make_url_request_using_cache(url, cache):
    if (url in cache.keys()): # the url is our unique key
        print("Using cache")
        return cache[url]
    else:
        print("Fetching")
        time.sleep(1)
        response = requests.get(url)
        cache[url] = response.text
        save_cache(cache)
        return cache[url]

class MovieInfo:
    def __init__(self, id = None, title = None, genre = None, ratings = None, director = None, actors = None, url = None, json = None):
        if json:
            self.id = json['imdbID']
            self.title = json['Title']
            self.genre = json['Genre']
            self.url = IMDb_URL+"/title/"+self.id
            if json['imdbRating'] == 'N/A':
                self.ratings = -1
            else:
                self.ratings = float(json['imdbRating'])
            self.director = json['Director'].split(',')[0]

            all_actors = json['Actors'].split(',')
            if len(all_actors)<=2:
                self.actors = ','.join(all_actors)
            else: 
                self.actors = ','.join(all_actors[0:2]) # a list, contains at most two names
        else:
            self.id = id
            self.title = title
            self.genre = genre
            self.ratings = ratings
            self.director = director
            self.actors = actors
            self.url = url
    def info(self):
        '''Print the ratings, director and the two main actors of the movie
        '''
        print('['+self.title+']'+' ('+self.ratings+')')
        print('Director: ' + self.director)
        print('Actors: ' + ','.join(self.actors))

class DirectorInfo:
    def __init__(self, name = None, url = None, related_movie_titles = []):
        self.name = name
        self.url  = url
        self.related_movie_titles = related_movie_titles


def get_movie_info_from_omdb(movie_title):
    '''Make a MovieInfo instance from the OMDb
    
    Parameters
    ----------
    movie_title: string
        The name of the movie to be searched in OMDb
    
    Returns
    -------
    instance
        a MovieInfo instance or None if the movie is not found in OMDb
    '''
    movie_title = movie_title.replace(" ","+")
    url = OMDb_BASE_URL + "&t=" + movie_title 
    json_str = make_url_request_using_cache(url, CACHE_DICT)
    dict_info = json.loads(json_str)
    if 'Error' in dict_info:
        return None
    else:
        movie = MovieInfo(json = dict_info)
        return movie

def get_director_url(movie):
    '''get the url of the director from a MovieInfo instance

    Parameters
    ----------
    movie: instance 
        an instance of MovieInfo
    
    Returns
    -------
    director_url: string
        a url of the director
    '''
    url = movie.url
    response_text = make_url_request_using_cache(url, CACHE_DICT)
    soup = BeautifulSoup(response_text, 'html.parser')
    people_div_list = soup.find_all('div', class_='credit_summary_item')
    for people_div in people_div_list:
        job = people_div.find('h4')
        if job.text == 'Director:' or job.text == 'Directors:':
            director_url = IMDb_URL + people_div.find('a')['href']
            return director_url

def get_director_instance(movie):
    '''Make a DirectorInfo instance from a url of the director

    Parameters
    ----------
    movie: instance
        an instance of MovieInfo
    
    Returns
    -------
    director: instance
        an instance of DirectorInfo
    '''
    director_url = get_director_url(movie)
    response_text = make_url_request_using_cache(director_url, CACHE_DICT)
    soup = BeautifulSoup(response_text, 'html.parser')
    name = soup.find('h1', class_ = 'header').find('span', class_ = 'itemprop').text
    related_movies = []
    director_info_list = soup.find_all('div', id=lambda x: x and x.startswith('director-'))
    for director_info in director_info_list:
        movie_title = director_info.find('b').find('a').text.lower()
        related_movies.append(movie_title)

    director = DirectorInfo(name = name, url = director_url, related_movie_titles=related_movies)
    return director
#########################################################################################



############ code for database processing ###############################################

def create_tables():
    conn = sqlite3.connect("MovieRecommend.sqlite")
    cur = conn.cursor()
    create_movie_table = '''
        CREATE TABLE IF NOT EXISTS "Movies" (
            "Id"      INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "Title"   TEXT NOT NULL,
            "imbdID"  TEXT NOT NULL,
            "Genre"   TEXT NOT NULL,
            "Ratings"  REAL NOT NULL,
            "Directors"  TEXT NOT NULL,
            "Actors"  TEXT NOT NULL,
            UNIQUE ("Title")
        );
    '''
    create_director_table = '''
            CREATE TABLE IF NOT EXISTS "Directors" (
            "Id"      INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            "Name"   TEXT NOT NULL,
            "URL"  TEXT NOT NULL,
            UNIQUE ("Name")
        );
    '''
    cur.execute(create_movie_table)
    cur.execute(create_director_table)
    conn.commit()

def insertItems_movie_table(Movie):
    '''insert a row in the "Movies" table

    Parameters
    ----------
    Movie: instance
        an instance of MovieInfo
    '''
    conn = sqlite3.connect("MovieRecommend.sqlite")
    cur = conn.cursor()
    insert_movie = '''
        INSERT OR IGNORE INTO Movies
        VALUES (NULL, ?,?,?,?,?,?)
    '''
    movie_info = (Movie.title, Movie.id, Movie.genre, Movie.ratings, Movie.director, Movie.actors)
    cur.execute(insert_movie, movie_info)
    conn.commit()

def insertItems_director_table(Director):
    '''insert a row in the "Directors" table

    Parameters
    ----------
    Director: instance
        an instance of DirectorInfo
    '''
    conn = sqlite3.connect("MovieRecommend.sqlite")
    cur = conn.cursor()
    insert_director = '''
        INSERT OR IGNORE INTO Directors
        VALUES (NULL, ?,?)
    '''
    director_info = [Director.name, Director.url]
    cur.execute(insert_director, director_info)
    conn.commit()
#############################################################################################


##################### code for main function of the project #################################
def creating_database():
    ''' create a database using the user input'''
    create_tables()
    #######################################################################################
    #### input a movie name, get the url and the director infor of the movie on IMDb,  ####
    #### scrape the movie page for the page of the director,                           ####
    #### scrape the director page for other movies directed by the director,           ####
    #### save the info of the related movies and the director in MovieRecommend.sqlite ####
    #######################################################################################    
    while True:
        movie_title = input("Input the title of a movie, or \"exit\" to exit step 1: ").lower().strip()
        if movie_title=="exit":
            break

        else:
            input_movie = get_movie_info_from_omdb(movie_title)
            if not input_movie:
                print("The movie is not found.")

            else:
                insertItems_movie_table(input_movie)
                director = get_director_instance(input_movie)
                insertItems_director_table(director)

                for directed_movie_title in director.related_movie_titles:
                    if directed_movie_title is not movie_title:
                        directed_movie = get_movie_info_from_omdb(directed_movie_title)
                        if directed_movie is not None: 
                            insertItems_movie_table(directed_movie)
    return 

def show_director_info():
    '''show two pie charts and one table about the info of a director in Plotly
    '''
    connection = sqlite3.connect("MovieRecommend.sqlite")
    cursor = connection.cursor()
    query = '''
    SELECT Name
    FROM Directors
    '''
    result = cursor.execute(query).fetchall()
    num_directors = len(result)
    print("Names of directors in the database are as the following: ")
    for i in range(num_directors):
        print(f"[{i+1}] {result[i][0]}")
    num_director_str = input("Please input the No. of director that you are interested in: ")
    while num_director_str.isnumeric() is False or int(num_director_str)>num_directors or int(num_director_str)==0:
        num_director_str = input("Pleass input a valid No. : ")
    director_idx = int(num_director_str)-1
    director_name = result[director_idx][0]
    director_result = cursor.execute("SELECT Title, Genre, Ratings FROM Movies where Directors=?", (director_name,)).fetchall()
    connection.close()
    #print(director_result)
    movie_dict = collections.defaultdict(list)
    genre_dict = {}
    rating_dict = {'N/A':0, '0~2':0, '2.1~4':0, '4.1~6':0, '6.1~8':0, '8.1~10':0}
    for movie in director_result:
        movie_dict['title'].append(movie[0])
        movie_dict['genre'].append(movie[1].split(',')[0])
        movie_dict['rating'].append(movie[2])
        if movie[1].split(',')[0] in genre_dict:
            genre_dict[movie[1].split(',')[0]] +=1
        else: genre_dict[movie[1].split(',')[0]] = 1
        if movie[2]==-1: rating_dict['N/A']+= 1
        elif movie[2]<=2: rating_dict['0~2']+= 1
        elif movie[2]<=4: rating_dict['2.1~4']+= 1
        elif movie[2]<=6: rating_dict['4.1~6']+= 1
        elif movie[2]<=8: rating_dict['6.1~8']+= 1
        else: rating_dict['8.1~10']+= 1
    #print(movie_dict)
    genre_pd = pd.DataFrame(genre_dict.items(), columns = ['genre','number'])
    #print(genre_pd)
    rating_pd = pd.DataFrame(rating_dict.items(), columns = ['rating range', 'number'])
    fig = make_subplots(
        rows=3, cols=1,
        #shared_xaxes=True,
        vertical_spacing=0.2,
        subplot_titles=['Distribution of genres',
            'Distribution of ratings',
            'table of titles, genres, and ratings'],
        specs=[[{"type": "pie"}],
           [{"type": "pie"}],
           [{"type": "table"}]]
    )
    fig.add_trace(go.Pie(values = genre_pd['number'], 
            labels = genre_pd['genre'], 
            hoverinfo="label+percent",),
            row = 1, col = 1)
    fig.add_trace(go.Pie(values = rating_pd['number'], 
            labels = rating_pd['rating range'],
            hoverinfo="label+percent"),
            row = 2, col = 1)
    fig.add_trace(go.Table(
            header=dict(values=['Movie Title', 'Genre', 'Rating']),
            cells=dict(values=[movie_dict['title'], movie_dict['genre'], movie_dict['rating']]),),
            row = 3, col = 1)
    # layout = go.Layout(xaxis = dict(domain = [0,1], title = 'x1'), yaxis = dict(domain = [0,0.5], title = 'y1'),
    #             xaxis2 = dict(domain = [0,0.5]), yaxis2 = dict(anchor = 'x2', domain = [0.6,1]),
    #             xaxis3 = dict(domain = [0,0.5]), yaxis3 = dict(anchor = 'x3', domain = [0.6,1]))
    fig = fig.update_layout(title_text = f'Summary of movies directed by {director_name}',
            margin=dict(l=100))
    # fig = go.Figure(data = data, layout = layout)
    fig.show()
    print("*"*50)

def show_info_about_movie_database():
    '''show two bar charts about the info of all the movies in the database
    '''
    connection = sqlite3.connect("MovieRecommend.sqlite")
    cursor = connection.cursor()
    query = '''
    SELECT Genre, Ratings
    FROM Movies
    '''
    result = cursor.execute(query).fetchall()
    connection.close()
    #num_movies = len(result)
    genre_dict = {}
    rating_dict = {'N/A':0, '0~2':0, '2.1~4':0, '4.1~6':0, '6.1~8':0, '8.1~10':0}
    for movie in result:
        if movie[0].split(',')[0] in genre_dict:
            genre_dict[movie[0].split(',')[0]] +=1
        else: genre_dict[movie[0].split(',')[0]] = 1
        if movie[1]==-1: rating_dict['N/A']+= 1
        elif movie[1]<=2: rating_dict['0~2']+= 1
        elif movie[1]<=4: rating_dict['2.1~4']+= 1
        elif movie[1]<=6: rating_dict['4.1~6']+= 1
        elif movie[1]<=8: rating_dict['6.1~8']+= 1
        else: rating_dict['8.1~10']+= 1
    #print(movie_dict)
    genre_pd = pd.DataFrame(genre_dict.items(), columns = ['genre','number'])
    #print(genre_pd)
    rating_pd = pd.DataFrame(rating_dict.items(), columns = ['rating range', 'number'])

    fig = make_subplots(
        rows=2, cols=1,
        #shared_xaxes=True,
        vertical_spacing=0.2,
        subplot_titles=['numbers of movies from all genres',
            'numbers of movies in all rating ranges'],
        specs=[[{"type": "bar"}],
           [{"type": "bar"}]]
    )
    fig.add_trace(go.Bar(x= genre_pd['genre'], 
            y = genre_pd['number'],
            name = 'movie numbers',
            text = genre_pd['number'], textposition = 'outside',
            cliponaxis = False),
            row = 1, col = 1)
    fig.add_trace(go.Bar(x = rating_pd['rating range'], 
            y = rating_pd['number'],
            name = 'movie numbers',
            text = rating_pd['number'], textposition = 'outside',
            cliponaxis = False),
            row = 2, col = 1)
    # layout = go.Layout(xaxis = dict(domain = [0,1], title = 'x1'), yaxis = dict(domain = [0,0.5], title = 'y1'),
    #             xaxis2 = dict(domain = [0,0.5]), yaxis2 = dict(anchor = 'x2', domain = [0.6,1]),
    #             xaxis3 = dict(domain = [0,0.5]), yaxis3 = dict(anchor = 'x3', domain = [0.6,1]))
    fig = fig.update_layout(title_text = 'Summary of movies in the database',
            margin=dict(l=100))
    # fig = go.Figure(data = data, layout = layout)
    fig.show()
    print("*"*50)

def movie_recommand_based_on_genre():
    '''print movie titles and rating based on the input genre
    '''
    genre = input("Please input a genre: ")
    connection = sqlite3.connect("MovieRecommend.sqlite")
    cursor = connection.cursor()
    query = '''
    SELECT Title, Genre, Ratings
    FROM Movies
    '''
    result = cursor.execute(query).fetchall()
    connection.close()
    print_result = []
    for movie in result:
        if movie[1].split(',')[0].lower() == genre:
            print_result.append((movie[0], movie[1].split(',')[0], movie[2]))
    if print_result == []:
        print("movie in the input genre does not exist in the database")
    else:
        title = f"{'No.':<5}{'Title':^50}{'Genre':^15}{'Rating':>5}"
        print("="*len(title))
        print(title)
        print("="*len(title))
        for i in range(len(print_result)):
            print(f"{i+1 : <5}{print_result[i][0]: ^50}{print_result[i][1]:^15}{print_result[i][2]: >5}")
        print("="*len(title))
    print("*"*50)

def movie_recommand_based_on_ranking():
    '''print movie titles and rating based on the input rating range
    '''
    print("The rating range: ")
    print("[1] 0 ~ 2")
    print("[2] 2.1 ~ 4")
    print("[3] 4.1 ~ 6")
    print("[4] 6.1 ~ 8")
    print("[5] 8.1 ~ 10")
    while True:
        rating_num_str = input("Please input a number of the rating range (from 1~5): ")
        if rating_num_str.isnumeric() is True and int(rating_num_str)>=1 and int(rating_num_str)<=5:
            break
        else:print("Please input a valid number. ")
    rating_num = int(rating_num_str)
    connection = sqlite3.connect("MovieRecommend.sqlite")
    cursor = connection.cursor()
    query = '''
    SELECT Title, Genre, Ratings
    FROM Movies
    '''
    result = cursor.execute(query).fetchall()
    connection.close()
    print_result = []
    for movie in result:
        if movie[2]>(rating_num-1)*2 and movie[2]<= rating_num*2:
            print_result.append((movie[0], movie[1].split(',')[0], movie[2]))
    if print_result == []:
        print("Movie in the rating range does not exist in the database.")
    else:
        title = f"{'No.':<5}{'Title':^50}{'Genre':^15}{'Rating':>5}"
        print("="*len(title))
        print(title)
        print("="*len(title))
        for i in range(len(print_result)):
            print(f"{i+1 : <5}{print_result[i][0]: ^50}{print_result[i][1]:^15}{print_result[i][2]: >5}")
        print("="*len(title))
    print("*"*50)

############################### main function ###############################################
def main():
    print("Welcome to the Movie Info database interactive application.")
    print("*"*50)
    print("Step 1: please input some movie titles to construct the database of movies and directors (more than 5 is better).")
    creating_database()
    print("*"*50)
    print("Step 2: please choose the application capability: ")
    print("1. Show the info about a director in the database." )
    print("2. Show the info about all the movies in the database.")
    print("3. Recommend some movies based on an input genre.")
    print("4. Recommend some movies based on the rating range.")
    print("*"*50)
    while True: 
        cap_num_str = input('Input an operation number or \"exit\" to exit the application: ')
        print("*"*50)
        if cap_num_str == 'exit': break

        elif cap_num_str.isnumeric() and int(cap_num_str)<=4 and int(cap_num_str)>=1:
            cap_num = int(cap_num_str)
            if cap_num == 1:
                show_director_info()
            elif cap_num == 2:
                show_info_about_movie_database()
            elif cap_num == 3:
                movie_recommand_based_on_genre()
            else:
                movie_recommand_based_on_ranking()
        else:
            print("Please input a valid number.")



if __name__ == "__main__":
    main()


    
