# importing our libraries

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd

import json
import time
import random
import datetime
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

boroughs = {"Plumstead": "5E85326",
    #"Southwark": "5E61518",
    #
    #"Greenwich": "5E61226",
    #"Woolwich": "5E70391",
    #"Nunhead": "5E70431",
    #"Lewisham": "5E61413",
    #"Hackney": "5E93953",
    #"Hammersmith and Fulham": "5E61407",
    #"Haringey": "5E61227",
    #"Harrow": "5E93956",
    #"Havering": "5E61228",
    #"Hillingdon": "5E93959",
    #"Hounslow": "5E93962",
    #"Islington": "5E93965",
    #"Kensington and Chelsea": "5E61229",
    #"Kingston upon Thames": "5E93968",
    #"Lambeth": "5E93971",
    #"Merton": "5E61414",
    #"Newham": "5E61231",
    #"Redbridge": "5E61537",
    #"Richmond upon Thames": "5E61415",
    #"Sutton": "5E93974",
    #"Tower Hamlets": "5E61417",
    #"Waltham Forest": "5E61232",
    #"Wandsworth": "5E93977",
    #"Westminster": "5E93980",
    #"City of London": "5E61224",
    #"Barking and Dagenham": "5E61400",
    #"Barnet": "5E93929",
    #"Bexley": "5E93932",
    #"Brent": "5E93935",
    #"Bromley": "5E93938",
    #"Camden": "5E93941",
    #"Croydon": "5E93944",
    #"Ealing": "5E93947",
    #"Enfield": "5E93950",
}

myheaders = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36" }

def scrape_links():

    all_links = []

    search_str = "".join(["https://www.rightmove.co.uk/property-for-sale/find.html?sortType=6",
                "&minBedrooms=2",
                "&maxPrice=375000",
                "&minPrice=100000",
                "&propertyTypes=detached%2Csemi-detached%2Cterraced",
                "&includeSSTC=false",
                "&mustHave=garden",
                "&dontShow=newHome%2Cretirement%2CsharedOwnership%2Cauction", # Don't show auctions
                "&locationIdentifier=REGION%"])# then append with location id and search page index 
    
    # The maximum page limit for rightmove is 42
    for borough_key, borough_id in boroughs.items():

        # initialise index, this tracks the page number we are on. every additional page adds 24 to the index
        index = 0
        
        logger.info(f"Scraping {borough_key}")
        
        for pages in range(41):
            
            searchUrl = search_str + borough_id + f"&index={index}"

            # request our webpage
            response = requests.get(searchUrl, headers=myheaders)

            # check status
            response.raise_for_status()

            logger.debug(f"{response.status_code}")
              
            soup = BeautifulSoup(response.text, "html.parser")

            # This gets the list of apartments
            houses = soup.find_all("div", class_="l-searchResult is-list")

            # This gets the number of listings
            number_of_listings = soup.find("span", {"class": "searchHeader-resultCount"}).get_text()
            number_of_listings = int(number_of_listings.replace(",", ""))

            for i, house in enumerate(houses):

                # append link
                apartment_info = house.find("a", class_="propertyCard-link")
                link = "https://www.rightmove.co.uk" + apartment_info.attrs["href"]
                all_links.append(link)

            #print(f"You have scrapped {pages + 1} pages of apartment listings.")
            #print(f"You have {number_of_listings - index} listings left to go")
            #print("\n")

            index = index + 24
            if index >= number_of_listings:
                break
            # code to make them think we are human
            time.sleep(random.randint(1, 3))

            
    logger.info("Searching complete. Returning links.")
    # convert data to dataframe
    data = {"Links": all_links,}
    
    df = pd.DataFrame.from_dict(data).drop_duplicates(keep='last')
    df.to_csv(r"scraped_links.csv", encoding="utf-8", header="true", index=False)

    return df


def scrape_link_info(link):
    
    logger.info(f"Extracting information from {link}")

    
    # request our page
    response = requests.get(link, headers=myheaders)

    # check status
    response.raise_for_status()
    
    logger.debug(f"Response status: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")
    
    page_info = soup.find(string=re.compile("window.PAGE_MODEL"))

    # remove javascript fluff from dict inside script
    jsonStr = re.search(r'\{.*\}', str(page_info)).group()
    
    #print(page_info)
    page_dict = json.loads(jsonStr)
    print("\n -------------- \n")
    for k in page_dict["propertyData"].keys():
            
        print("\n -------------- \n")
        print(k,"    -------------\n")
        print(page_dict["propertyData"][k])

    print("\n -------------- \n")
    print(page_dict.keys())
    
    print("\n ------analyticsInfo-------- \n")
    print(page_dict["analyticsInfo"])
    print("\n -------------- \n")
    print(page_dict["propertyData"]["text"]["shareDescription"])

    property_dict = page_dict["propertyData"]
    property_id = property_dict['id']
    status = property_dict['status']
    description = property_dict['text']['description']
    short_description = property_dict['text']['shareDescription']
    address = property_dict['address']['displayAddress']
    price = property_dict['prices']['primaryPrice']
    num_bedrooms = property_dict['bedrooms']
    postcode = property_dict['address']['outcode'] + " " + property_dict['address']['incode']
    nearest_stations = [(station['name'], station['distance']) for station in property_dict['nearestStations']]



    {'analyticsBranch': {'agentType': 'ea_sales', 'branchId': 237332, 'branchName': 'London', 'branchPostcode': None, 'brandName': 'McHugh & Co', 'companyName': 'McHugh & Co', 'companyTradingName': 'McHugh & Co', 'companyType': 'iea', 'displayAddress': '71 Parkway,\r\nLondon,\r\nNW1 7PP', 'pageType': 'Standard'}, 'analyticsProperty': {'added': '20230503', 'auctionOnly': True, 'beds': 3, 'businessForSale': False, 'country': 'GB', 'currency': 'GBP', 'floorplanCount': 0, 'furnishedType': 'Not Specified', 'hasOnlineViewing': False, 'imageCount': 1, 'latitude': 51.48695, 'longitude': 0.09723, 'letAgreed': False, 'lettingType': 'Long term', 'maxSizeAc': None, 'maxSizeFt': None, 'minSizeAc': None, 'minSizeFt': None, 'ownership': 'Non-shared ownership', 'postcode': 'SE18 1HW', 'preOwned': 'Resale', 'price': 290000, 'priceQualifier': 'Guide Price', 'propertyId': 134401997, 'propertySubType': 'Terraced', 'propertyType': 'Houses', 'retirement': False, 'selectedCurrency': None, 'selectedPrice': None, 'soldSTC': False, 'videoProvider': 'No Video', 'viewType': 'Current', 'customUri': 'https://www.rightmove.co.uk/property-for-sale/properties'}}

    agent = page_dict["analyticsInfo"]["analyticsBranch"]["brandName"]
    contact_email = None
    contact_phone = None
    
    info = {"Link": link,
            "Price": price,
            "Name": None,
            "Description": None,#description,
            "Short Description": short_description,
            "Bedrooms": None,
            "Bathrooms": None,
            "Property type" : None,
            "Address": address,
            "Postcode": postcode,
            "Garden": None,
            "Floorplan": None,
            "Freehold": None,
            'Nearest Stations': nearest_stations,}
    
    print(info)
    return 1


if __name__ == "__main__":

    link = "https://www.rightmove.co.uk/properties/134401997#/?channel=RES_BUY"
    scrape_link_info(link)

    # Scrape the property links
    #linkdf = scrape_links()
    


    #link_infos = [None,]*len(linkdf)
    #for i, link in enumerate(linkdf["Links"]):
    #    print(i,link)
    #    info = scrape_link_info(link)
    #    link_infos[i] = info
    #    break

    #print(link_infos)