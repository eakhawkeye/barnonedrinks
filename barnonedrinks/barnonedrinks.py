#!python
# BarNonDrinks.py - BarNonDrinks.com database and searcher
# by EakHawkEye
# Requires Python3 unidecode (pip install unidecode)


import argparse
import copy
import random
import re
import requests
import shelve
import string
import sys
import textwrap
import time
from bs4 import BeautifulSoup
from pathlib import Path
from unidecode import unidecode


barnone_url_drinks= 'https://www.barnonedrinks.com/drinks/'
barnone_url_ingredients = 'https://www.barnonedrinks.com/drinks/by_ingredient/'
user_agent = 'Mozilla/5.0 (Android 4.4; Tablet; rv:41.0) Gecko/41.0 Firefox/41.0'
dct_bndrinks = {}
dct_canmake = {}
dct_recipes = {}
my_ingredients = []
bnd_ingredients = []


class Shelver:
    # Shelve helper class
    def __init__(self, shelve_file):
        self.shelve_file = shelve_file
    def write(self, key, value):
        with shelve.open(self.shelve_file, 'c') as db:
            db[key] = value
    def read(self, key):
        with shelve.open(self.shelve_file, 'r') as db:
            return db.get(key)

def importIngredients(import_file, shelf_db):
    """Import ingredients from file"""
    print('Importing ingredients from file...')
    my_ingredients = []
    with open(import_file, 'r') as f:
        for line in f:
            my_ingredients.append(line.strip())
    shelf_db.write('my_ingredients', my_ingredients)

def scrapePage(url, user_agent):
    """Scrape the BND website and return the results in a dictionary"""
    global dct_bndrinks
    is_base = 'by_ingredient/'
    response = requests.get(url, headers={'User-Agent': user_agent})
    if response.status_code == 200:
        print('\t{}'.format(url))
        soup = BeautifulSoup(response.text, 'html.parser')
        if url.endswith(is_base):
            div = soup.find_all('div', {'class': 'bnd-c-nav'})[0]
        else:
            div = soup.find_all('div', {'class': 'bnd-c-text-sect'})[0]
        # if div finds a list of drinks parse and store...
        dt_tags = div.find_all('dt')
        if dt_tags:
            for i in range(len(dt_tags)):
                drink_type = re.split('\(|\)', dt_tags[i].text)
                drink = drink_type[0].strip()
                type = drink_type[1].strip()
                raw_ingredients = dt_tags[i].find_next_sibling('dd').text.split(',')
                ingredients = [ i.strip() for i in raw_ingredients ]
                drink_link = dt_tags[i]('a')[0].get('href').replace('../','')
                # Store drinks in dictionary
                dct_bndrinks.update({
                    drink: {
                        'type': type, 
                        'ingredients': ingredients, 
                        'url': barnone_url_drinks + drink_link 
                    }
                })
        # else continue crawling              
        else:
            links = div.find_all('a')
            for link in links:
                #time.sleep(random.randint(1, 3))
                scrapePage(url + link.get('href'), user_agent)

def prepareRecipes(dct_matches, dct_bndrinks, dct_recipes, search_terms, get_all=False):
    """Download and build list of recipe instructions"""
    if not dct_recipes:
        dct_recipes = {}
    search_count = len(search_terms)
    for name in dct_matches.keys():
        # Only process exact matches or everything if requested
        if not search_count == len(dct_matches[name]) and not get_all:
            continue
        # Download the recipe
        if not name in dct_recipes.keys():
            print("Downloading Recipe for {}".format(name))
            dct_recipes[name] = copy.deepcopy(dct_bndrinks[name])
            response = requests.get(dct_recipes[name]['url'], headers={'User-Agent': user_agent})
            if response.status_code == 200:
                # <ul class="bningredients">
                # <li>1 1/2 oz. <a href="../by_ingredient/p/passion-fruit-syrup-672.html">Passion Fruit Syrup</a> </li>
                # <li><a href="../by_ingredient/o/orange-juice-73.html">Orange Juice</a> (Fresh)</li>
                # </ul>           <h2 class="bndrinksect">Instructions</h2>
                # <div class="bnd-c-text-sect" >...text stuff...</div>
                soup = BeautifulSoup(response.text, 'html.parser')
                portions = []
                div_portions = soup.find_all('ul', {'class': 'bningredients'})
                # iterate through each item of the list <ul..>
                for l in div_portions[0].find_all('li'):
                    # get the list item's link's _text_ (<a..>_text_</a>)
                    l_ingredient = l.find_all('a')[0].text.strip()
                    # Dedupe, clean input, and remove empty elements
                    l_rawtexts = re.split(l_ingredient, l.text)
                    l_texts = list(filter(None, [ e.strip() for e in l_rawtexts ]))
                    # Split the list item depending on the remining elements
                    if len(l_texts) == 0:
                        l_portion = '.'
                    elif len(l_texts) == 1:
                        if not l_texts[0][0].isdigit():
                            l_portion = '.'
                            l_ingredient = l_texts[0]
                        else:
                            l_portion = l_texts[0]
                    else:
                        if not l_texts[0][0].isdigit():
                            l_portion = '.'
                            l_ingredient = '%s - %s' % (l_texts[0], l_texts[1])
                        else:
                            l_portion = l_texts[0]
                            l_ingredient += '(%s)' % (l_texts[1])
                    # build the list of portion tuples
                    portions.append((l_portion, l_ingredient))
                dct_recipes[name]['portions'] = portions                
                div_instructions = soup.find_all('div', {'class': 'bnd-c-text-sect'})[0]
                dct_recipes[name]['instructions'] = unidecode(div_instructions.text)
            else:
                print("Error downloading recipe {}".format(name))
    return dct_recipes

def buildDictionaryOfDrinks(url, user_agent, shelf_db):
    """Build the dictionary of drinks"""
    global dct_bndrinks
    dct_bndrinks = {}
    print('Scraping barenonedrinks.com...')
    # Scrape the bnd website
    scrapePage(url, user_agent)
    print('\tScrape complete!')
    shelf_db.write('dct_bndrinks', dct_bndrinks)
    print('\tDatabase built!')

def buildDictionaryOfIngredients(dct_bndrinks, shelf_db):
    """Build the list of complete ingredients"""
    global bnd_ingredients
    build_ingredients = set()
    print('Building list of complete BND ingredients...')
    for drink in dct_bndrinks.keys():
        build_ingredients.update(dct_bndrinks[drink]['ingredients'])
    build_ingredients = sorted(list(build_ingredients))
    shelf_db.write('bnd_ingredients', build_ingredients)
    print('\tList built')

def buildDictionaryOfCanMakeDrinks(dct_bndrinks, my_ingredients, shelf_db):
    """Build the dictionary of can make drinks"""
    print('Building dictionary of can make drinks...')
    dct_canmake = {}
    hash_my_ingredients = set([ unidecode(i.lower()) for i in my_ingredients ])
    for drink in dct_bndrinks.keys():
        match = True
        d_i = dct_bndrinks[drink]['ingredients']
        d_t = dct_bndrinks[drink]['type']
        d_u = dct_bndrinks[drink]['url']
        for i in d_i:
            is_strict = False if len(i) > 1 else True
            if not isHere(i, hash_my_ingredients, is_strict, True):
                match = False
                break
        if match:
            dct_canmake[drink] = {'ingredients': d_i, 'url': d_u, 'type': d_t}
    shelf_db.write('dct_canmake', dct_canmake)

def isHere(term, obj, strict=False, reverse_search=False):
    """Is the term in the object?"""
    # Normalize then use set() to dedupe and be efficient in searching
    term = unidecode(term).lower()
    if isinstance(obj, str):
        content = set([ unidecode(obj).lower() ])
    elif isinstance(obj, list) or isinstance(obj, set):
        content = set([ unidecode(o).lower() for o in obj ])
    else:
        print('Cannot process object passsed to isHere for type {}'.format(type(obj)))
        sys.exit(1)
    # Search if the term matches any items in the object
    # |- strict:  term("raspberry liqueur") == c("raspberry liqueur")
    # |- loose:   term("raspberry liqueur") ~= c("chambord raspberry liqueur")
    # |- reverse: term("chambord raspberry liqueur") ~= c("raspberry liqueur")
    for c in content:
        if term == c:
            return True
        if not strict and term in c:
            return True
        if (reverse_search and 
            len(c.split()) > 1 and
            c in term):
            return True
    return False

def searchGeneral(search_terms, dct_search, dct_recipes):
    """Search everything for term matches."""
    dct_matches = {}
    dct_drink_m = searchDrinks(search_terms, dct_search)
    dct_ingredient_m = searchIngredients(search_terms, dct_search)
    dct_type_m = searchTypes(search_terms, dct_search)
    dct_recipe_m = searchRecipes(search_terms, dct_recipes)
    dct_matches = searchAggregate({}, dct_drink_m, dct_ingredient_m, dct_type_m, dct_recipe_m)
    return dct_matches

def searchDrinks(search_terms, dct_search):
    """Search drink names for term matches."""
    dct_matches = {}
    for name, drink in dct_search.items():
        for term in search_terms:
            if isHere(term, name):
                dct_matches.setdefault(name, []).append(term)
    return dct_matches

def searchIngredients(search_terms, dct_search):
    """Search ingredients for term matches."""
    dct_matches = {}
    for name, drink in dct_search.items():
        for term in search_terms:
            if isHere(term, drink['ingredients']):
                dct_matches.setdefault(name, []).append(term)
    return dct_matches

def searchTypes(search_terms, dct_search):
    """Search types for term matches."""
    dct_matches = {}
    for name, drink in dct_search.items():
        for term in search_terms:
            if isHere(term, drink['type']):
                dct_matches.setdefault(name, []).append(term)
    return dct_matches

def searchRecipes(search_terms, dct_recipes):
    """Search recipe instructions for term matches."""
    dct_matches = {}
    for name, drink in dct_recipes.items():
        for term in search_terms:
            if isHere(term, drink['instructions']):
                dct_matches.setdefault(name, []).append(term)
    return dct_matches

def searchAggregate(dct_general_m, dct_name_m, dct_ingredient_m, dct_type_m, dct_recipe_m):
    """Merge search result dictionaries"""
    dct_matches = {}
    for name in dct_general_m.keys():
        dct_matches.setdefault(name, []).extend(dct_general_m[name])
    for name in dct_name_m.keys():
        dct_matches.setdefault(name, []).extend(dct_name_m[name])
    for name in dct_ingredient_m.keys():
        dct_matches.setdefault(name, []).extend(dct_ingredient_m[name])
    for name in dct_type_m.keys():
        dct_matches.setdefault(name, []).extend(dct_type_m[name])
    for name in dct_recipe_m.keys():
        dct_matches.setdefault(name, []).extend(dct_recipe_m[name])
    for name in dct_matches.keys():
        dct_matches[name] = list(set(dct_matches[name]))
    return dct_matches

def displayAvailableDrinks(dct):
    """Display available drinks"""
    for name in dct.keys():
        d_i = ', '.join(dct[name]['ingredients'])
        d_t = dct[name]['type']
        print("{} ({}): {}".format(name, d_t, d_i))
            
def displayResults(dct_search, search_terms=[], dct_matches={}, show_recipes=False, dct_rcp={}):
    """Display search results"""
    sorted_matches = sorted(dct_matches.items(), key=lambda x: len(x[1]), reverse=True)
    search_count = len(search_terms)
    results_count = 0
    for name, matches in sorted_matches:
        # Only display exact search term matches
        if search_count == len(matches):
            # dct_recipes can include unmakeable drinks based on my_ingredients changes
            try:
                d_i = ', '.join(dct_search[name]['ingredients'])
            except KeyError:
                continue
            d_t = dct_search[name]['type']
            d_u = dct_search[name]['url']
            results_count += 1
            # Format different if displaying recipes
            if show_recipes:
                d_p = dct_rcp[name]['portions']
                d_r = dct_rcp[name]['instructions']
                print("\n{} ({}):".format(name, d_t))
                [ print("\t  {:.<12}{}".format(p[0], p[1])) for p in d_p ]
                # Output instructions with limited width
                format_r = re.sub("\s+", ' ', d_r).lstrip()
                format_r = textwrap.wrap(format_r,
                      width=70,
                      initial_indent='\t',
                      subsequent_indent='\t',
                      drop_whitespace=True)                
                [ print("{}".format(line)) for line in format_r ]
                print("\t{}".format(d_u))
            else:
                print("\n{} ({}): {}".format(name, d_t, d_i))
                print("\t{}".format(d_u))
    print("\nResults: {}".format(results_count))

def displayStats(my_ingredients, dct_bndrinks, dct_canmake, bnd_ingredients):
    """Display statistics"""
    type_counts = {}
    # Count the types of drinks we're able to make and sort
    for item in dct_canmake.values():
        type = item['type']
        if type in type_counts:
            type_counts[type] += 1
        else:
            type_counts[type] = 1
    sorted_counts = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
    # Display ingredient count
    print('{:>15}: {}'.format('Ingredients', len(my_ingredients)))
    # Display the number of drinks we can make
    print('{:15}: {}'.format('Makeable Drinks', len(dct_canmake)))
    # Display the number of types of drinks we can make in desc drder
    for type, count in sorted_counts:
        if count > 1:
            print('{:>15}: {}'.format(type, count))
    # Display the total drinks acquired in the bnd database
    print('{:>15}: {}'.format('Total Drinks', len(dct_bndrinks)))

def displayConversions():
    """Display general conversions to ounces"""
    conversions = [ 
                   ('1 cup', '25/3 oz'),
                   ('1 shot', '3/2 oz'),
                   ('1 tbsp', '1/2 oz'), 
                   ('1 tsp', '1/6 oz'), 
                   ('1 ml', '1/30 oz') ]
    for cons in conversions:
        print('{:>10} = {:>7}'.format(cons[0], cons[1]))

def displayIngredientAlts(dct_ingredient_alts):
    """Display ingredient alternatives"""
    for my, bnds  in dct_ingredient_alts.items():
        print('{}:'.format(my))
        [ print('\t{}.format(i)') for i in bnds ]

def main():
    global dct_bndrinks
    global dct_canmake
    global my_ingredients
    global bnd_ingredients
    global dct_recipes
    dct_type_m = {}
    dct_drink_m = {}
    dct_general_m = {}
    dct_ingredient_m = {}
    dct_recipe_m = {}
    all_search_terms = []

    parser = argparse.ArgumentParser()
    parser.add_argument("dynamic",
                        default=None,
                        metavar='type(s) | unique name', 
                        nargs='*',
                        help='type(s) or name of pokemon, space separated')
    parser.add_argument("--all",
                        default=False,
                        action='store_true',
                        help='output all relevant drinks (default: only what you can make)')
    parser.add_argument("--list", '-l',
                        default=False,
                        action='store_true',
                        help='output all ingredients stored')
    parser.add_argument("--add",
                        default=[],
                        nargs='+',
                        help="add an ingredient, space separated")
    parser.add_argument("--remove",
                        default=[],
                        nargs='+',
                        help='remove an ingredient')
    parser.add_argument("--drinks", "-d",
                        default=[],
                        nargs='+',
                        help="search by drink name")
    parser.add_argument("--ingredients", "-i",
                        default=[],
                        nargs='+',
                        help="search by ingredient")
    parser.add_argument("--instructions", "-r",
                        default=[],
                        nargs='+',
                        help="search by instructions (recipes)")
    parser.add_argument("--types", "-t",
                        default=[],
                        nargs='+',
                        help="search by type")
    parser.add_argument("--stats", "-s",
                        default=False,
                        action='store_true',
                        help='display the stats of the database')
    parser.add_argument("--file",
                        type=lambda p: Path(p).absolute(),
                        default=Path.home().absolute() / ".barnonedrinks.db",
                        required=False,
                        help="specify a shelve file")
    parser.add_argument("--rebuild",
                        default=False,
                        action='store_true',
                        help='scrape site and rebuild dct_bndrinks')
    parser.add_argument("--importingredients",
                        type=lambda p: Path(p).absolute(),
                        default=None,
                        required=False,
                        help="Import ingredients from a file, line separated")
    parser.add_argument("--recipes",
                        default=False,
                        action='store_true',
                        help="Display recipes of the search results. Download if missing except when using --all")
    parser.add_argument("--conversions", "-c",
                        default=False,
                        action='store_true',
                        help="Display conversions to ounces")
    parser.add_argument("--ingredientalts",
                        default=False,
                        action='store_true',
                        help="Display all related (alt) ingredients")
    args = parser.parse_args()

    # Load DB from file
    shelf_db = Shelver(str(args.file))
    try:
        dct_bndrinks = shelf_db.read('dct_bndrinks')
        dct_canmake = shelf_db.read('dct_canmake')
        my_ingredients = shelf_db.read('my_ingredients')
        dct_recipes = shelf_db.read('dct_recipes')
        bnd_ingredients = shelf_db.read('bnd_ingredients')
    except:
        pass

    # First run
    if not dct_bndrinks:
        print('First run! We need to setup a few things so please wait...')
        shelf_db.write('my_ingredients', [])
        shelf_db.write('dct_canmake', {})
        buildDictionaryOfDrinks(barnone_url_ingredients, user_agent, shelf_db)
        print('Next, run me again but this time add some ingradients with the --add option!')

    # Import ingredients from a file
    if args.importingredients:
        import_file = str(args.importingredients)
        importIngredients(import_file, shelf_db)
        my_ingredients = shelf_db.read('my_ingredients')
        buildDictionaryOfCanMakeDrinks(dct_bndrinks, my_ingredients, shelf_db)
        dct_canmake = shelf_db.read('dct_canmake')

    # Add ingredients to my_ingredients
    if args.add:
        for i in args.add:
            i = i.translate(str.maketrans('', '', string.punctuation)).strip().title()
            try:
                my_ingredients.append(i)
            except AttributeError:
                my_ingredients = [i]
                print('error')
            print('Added: {}'.format(i))
        # Clean duplicates
        my_ingredients = list(set(my_ingredients))
        shelf_db.write('my_ingredients', my_ingredients)
        my_ingredients = shelf_db.read('my_ingredients')
        # Recreate the diction of drinks we can make
        buildDictionaryOfCanMakeDrinks(dct_bndrinks, my_ingredients, shelf_db)
        dct_canmake = shelf_db.read('dct_canmake')
    
    # Remove ingredients from my_ingredients
    if args.remove:
        for i in args.remove:
            try:
                my_ingredients.remove(i)
                print('\tIngredient removed: {}'.format(i))
            except:
                pass
        shelf_db.write('my_ingredients', my_ingredients)
        my_ingredients = shelf_db.read('my_ingredients')
        # Recreate the diction of drinks we can make
        buildDictionaryOfCanMakeDrinks(dct_bndrinks, my_ingredients, shelf_db)
        dct_canmake = shelf_db.read('dct_canmake')

    # If no ingredients, exit
    if not my_ingredients:
        print("Please add at least one ingredient using the --add option")
        sys.exit(0)

    # List all my ingredients
    if args.list:
        for i in sorted(my_ingredients):
            print(i)

    # Rebuild by scraping the site
    if args.rebuild:
        dct_bndrinks = {}
        dct_canmake = {}
        # Build the dictionary of BND drinks
        print('Scraping barenonedrinks.com...')
        buildDictionaryOfDrinks(barnone_url_ingredients, user_agent, shelf_db)
        dct_bndrinks = shelf_db.read('dct_bndrinks')
        print('\tScrape complete!')
        # Build the list of BND ingredients
        buildDictionaryOfIngredients(dct_bndrinks, shelf_db)
        bnd_ingredients = shelf_db.read('bnd_ingredients')
        # Build the dictionary of can make drinks
        buildDictionaryOfCanMakeDrinks(dct_bndrinks, my_ingredients, shelf_db)
        dct_canmake = shelf_db.read('dct_canmake')
    
    # This should never happen
    if not dct_canmake:
        print('canmake is missing')
        # Build the dictionary of can make drinks
        buildDictionaryOfCanMakeDrinks(dct_bndrinks, my_ingredients, shelf_db)
        dct_canmake = shelf_db.read('dct_canmake')

    # Download all the recipes for dct_canmake
    if len(sys.argv) == 2 and args.recipes:
        print('Downloading all the recipes for drinks you can make...')
        # Build the dictionary of recipes
        prepareRecipes(dct_canmake, dct_bndrinks, dct_recipes, [], True)
        shelf_db.write('dct_recipes', dct_recipes)

    # Define the search dictionary (either dct_canmake or dct_bndrinks)
    dct_search = dct_bndrinks if args.all else dct_canmake
    
    # Search: General
    if args.dynamic:
        search_terms = args.dynamic
        dct_general_m = searchGeneral(search_terms, dct_search, dct_recipes)
        all_search_terms.extend(search_terms)
    
    # Search: Drinks
    if args.drinks:
        search_terms = args.drinks
        dct_drink_m = searchDrinks(search_terms, dct_search)
        all_search_terms.extend(search_terms)
    
    # Search: Ingredients
    if args.ingredients:
        search_terms = args.ingredients
        dct_ingredient_m = searchIngredients(search_terms, dct_search)
        all_search_terms.extend(search_terms)
    
    # Search: Types
    if args.types:
        search_terms = args.types
        dct_type_m = searchTypes(search_terms, dct_search)
        all_search_terms.extend(search_terms)

    # Search: Recipes / Instrutions
    if args.instructions:
        search_terms = args.instructions
        dct_recipe_m = searchRecipes(search_terms, dct_recipes)
        all_search_terms.extend(search_terms)
    
    # Search Aggregate
    if all_search_terms:
        dct_matches = searchAggregate(dct_general_m, 
                                      dct_drink_m, 
                                      dct_ingredient_m, 
                                      dct_type_m,
                                      dct_recipe_m)
        # If we're displaying recipes...
        if args.recipes:
            # Ensure that we have the recipes in our recipes DB
            dct_recipes = prepareRecipes(dct_matches, dct_bndrinks, dct_recipes, all_search_terms)
            shelf_db.write('dct_recipes', dct_recipes)
            dct_recipes = shelf_db.read('dct_recipes')
        displayResults(dct_search, all_search_terms, dct_matches, args.recipes, dct_recipes)

    # Display the stats
    if args.stats:
        displayStats(my_ingredients, dct_bndrinks, dct_canmake, bnd_ingredients)

    # Display general conversions
    if args.conversions:
        displayConversions()

    # List drinks we're able to make
    if len(sys.argv) == 1:
        displayAvailableDrinks(dct_canmake)

if __name__ == "__main__":
    main()