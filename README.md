# 507Final_project


## required packages:
bs4, requests, sqlite3, plotly, pandas


## instructions on how to interact with the program:
The user inputs are titles of movies, then the program will use the OMDb to get the basic info of the movie and scrape the page of the director to collect information about other movies directed by the same director. The information of movies and directors will be stored in a database.
Finally, with the database, the user can choose some application capabilities to get some information about directors and movies in the database.

## introduction of files:
 - final_project_jiahongx.py: main function file
 - cache.json: a cache file
 - MovieRecommend.sqlite: a sample database (this is not required for running the main function) 

## keys for OMDb API:
the api is contained in the code in the final_project_jiahongx.py line 19. 

