# barnonedrinks
Scrape and Search tool for BarNoneDrinks

I love this site but I find it difficult to discover what I can make based off ingredients. Due to the site's great design, it's easy to see one ingredient's possibilities but not multiple and so on. Hopefully this tool helps fill the gaps.

```
-$ ./barnonedrinks.py --help
usage: barnonedrinks.py [-h] [--all] [--list] [--add ADD [ADD ...]] [--remove REMOVE [REMOVE ...]]
                        [--drinks DRINKS [DRINKS ...]] [--ingredients INGREDIENTS [INGREDIENTS ...]]
                        [--instructions INSTRUCTIONS [INSTRUCTIONS ...]] [--types TYPES [TYPES ...]] [--stats] [--file FILE]
                        [--rebuild] [--importingredients IMPORTINGREDIENTS] [--recipes] [--conversions] [--ingredientalts]
                        [types | unique name ...]

positional arguments:
  general search terms  search through all categories

options:
  -h, --help            show this help message and exit
  --all                 output all relevant drinks (default: only what you can make)
  --list, -l            output all ingredients stored
  --add ADD [ADD ...]   add an ingredient, space separated
  --remove REMOVE [REMOVE ...]
                        remove an ingredient
  --drinks DRINKS [DRINKS ...], -d DRINKS [DRINKS ...]
                        search by drink name
  --ingredients INGREDIENTS [INGREDIENTS ...], -i INGREDIENTS [INGREDIENTS ...]
                        search by ingredient
  --instructions INSTRUCTIONS [INSTRUCTIONS ...], -r INSTRUCTIONS [INSTRUCTIONS ...]
                        search by instructions (recipes)
  --types TYPES [TYPES ...], -t TYPES [TYPES ...]
                        search by type
  --stats, -s           display the stats of the database
  --file FILE           specify a shelve file
  --rebuild             scrape site and rebuild dct_bndrinks
  --importingredients IMPORTINGREDIENTS
                        Import ingredients from a file, line separated
  --recipes             Display recipes of the search results. Download if missing except when using --all
  --conversions, -c     Display conversions to ounces
  --ingredientalts      Display all related (alt) ingredients
