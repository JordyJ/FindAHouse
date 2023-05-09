# importing our libraries

import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import json
import time
import random
import logging


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

boroughs = {"Plumstead": "5E85326",
    "Southwark": "5E61518",
    "Greenwich": "5E61226",
    "Woolwich": "5E70391",
    "Nunhead": "5E70431",
    "Lewisham": "5E61413",
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
                "&maxPrice=425000",
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

    logger.info(f"Unique property links found: {len(df)}")

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
    page_dict = json.loads(jsonStr)

    
    """for k in page_dict.keys():
        break
        try:
            for k2 in page_dict[k].keys():
                print("\n -------------- \n")
                print(k,k2,"\n")
                print(page_dict[k][k2])
        except:
            pass
    """

    property_dict = page_dict["propertyData"]
    property_id = property_dict['id']
    property_type = property_dict["propertySubType"]
    
    price = property_dict['prices']['primaryPrice']
    num_bedrooms = property_dict['bedrooms']
    num_bathrooms = property_dict['bathrooms']
    
    status = property_dict['status']
    description = property_dict['text']['description']
    short_description = property_dict['text']['shareDescription']
    address = property_dict['address']['displayAddress']
    
    postcode = property_dict['address']['outcode'] + " " + property_dict['address']['incode']
    nearest_stations = [(station['name'], station['distance']) for station in property_dict['nearestStations']]

    freehold = (page_dict["propertyData"]['tenure']['tenureType']=="FREEHOLD")
    #print("freehold",page_dict["propertyData"]['tenure']['tenureType'] == "FREEHOLD")
    leaseremaining = page_dict["propertyData"]['tenure']['yearsRemainingOnLease']
    
    agent = page_dict["analyticsInfo"]["analyticsBranch"]["brandName"]

    # Find garden details from the targeting list (bit cryptic)
    targeting_list = property_dict["dfpAdInfo"]["targeting"]

    # Determine if garden is a feature in the targeting list
    feature_tmp = [ tmp_dict['value'] for tmp_dict in property_dict["dfpAdInfo"]["targeting"] if tmp_dict['key'] == "F" ][0]
    hasGardenfeature = ("garden" in feature_tmp)

    # Find EPC details
    hasEPCimage = False
    EPCUrl = None
    if property_dict["epcGraphs"] != []:
        hasEPCimage = True
        EPCUrl = property_dict["epcGraphs"][0]["url"]

    # Find floorplan details    
    floorplan = False
    floorplanURL = None
    if property_dict["floorplans"] != []:
        floorplan = True
        floorplanURL = property_dict["floorplans"][0]["url"]

    # Find image urls
    
    info = {"Link": link,
            "Price": price,
            "Description": description,
            "Short Description": short_description,
            "Bedrooms": num_bedrooms,
            "Bathrooms": num_bathrooms,
            "Property type" : property_type,
            "Address": address,
            "Postcode": postcode,
            "Garden": hasGardenfeature,
            "Floorplan": floorplan,
            "Floorplan URL": floorplanURL,
            "EPC image" : hasEPCimage,
            "EPC URL" : EPCUrl,
            "Freehold": freehold,
            "Lease Remaining": leaseremaining,
            'Nearest Stations': nearest_stations,
            "Agent": agent,
            }
    

    # EPC extraction
    # Lead image extraction
    # Image extraction for analysis

    return info


if __name__ == "__main__":

    #link = "https://www.rightmove.co.uk/properties/134401997#/?channel=RES_BUY"
    #link = "https://www.rightmove.co.uk/properties/128062247#/?channel=RES_BUY"
    
    #scrape_link_info(link)

    # Scrape the property links
    
    linkdf = scrape_links()

    link_infos = [None,]*len(linkdf)
    for i, link in enumerate(linkdf["Links"]):
        
        logger.info(f"Property {i}")
        info = scrape_link_info(link)
        link_infos[i] = info
    
      
    timestr = time.strftime("%Y%m%d_%H_%M_%S")
    filename = "search_result_" + timestr + ".csv"
    df = pd.DataFrame(link_infos)
    df.to_csv(filename, encoding="utf-8", header="true", index=False)
    #print(link_infos)