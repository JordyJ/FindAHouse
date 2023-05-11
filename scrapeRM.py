import requests
from bs4 import BeautifulSoup
import re
import pandas as pd
import json
import time
from datetime import datetime, timedelta
import random
import logging
import shutil


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOROUGHS = {
    "Southwark": "5E61518",
    "Greenwich": "5E61226",
    #"Woolwich": "5E70391",
    #"Nunhead": "5E70431",
    #"Lewisham": "5E61413",
    #"Hackney": "5E93953",
    #"Plumstead": "5E85326",
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

MY_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36" }
RESULTS_PER_PAGE = 24
MAX_NUM_PAGES = 41

def scrape_links_across_boroughs(search_str, boroughs):
    # Scrapes property links on rightmove that satisfy the search_str across a list of boroughs
    # Returns a list of unique links to properties

    all_links = []

    if "rightmove.co.uk" not in search_str:
        raise ValueError("search_str must contain a rightmove.co.uk url")
    
    for borough_key, borough_id in boroughs.items():

        
        logger.info(f"Scraping {borough_key}")

        search_url = search_str + borough_id
        
        all_links.extend(scrape_links(search_url))
                    
    logger.info("Searching complete. Returning links.")
    
    data = {"Links": all_links,}
    df = pd.DataFrame.from_dict(data).drop_duplicates(keep='last')
    df.to_csv(r"scraped_links.csv", encoding="utf-8", header="true", index=False)

    logger.info(f"Unique property links found: {len(df)}")

    return df

    


def scrape_links(url):
    # Scrapes links on Rightmove to properties that match the search terms defined in the url
    index = 0
    property_links = []

    for page_number in range(MAX_NUM_PAGES):
            
        search_url = url + f"&index={index}"

        # request our webpage
        response = requests.get(search_url, headers=MY_HEADERS)

        # check status
        response.raise_for_status()
        logger.debug(f"{response.status_code}")
            
        soup = BeautifulSoup(response.text, "html.parser")

        properties = soup.find_all("div", class_="l-searchResult is-list")

        # This gets the number of listings
        number_of_listings = soup.find("span", {"class": "searchHeader-resultCount"}).get_text()
        number_of_listings = int(number_of_listings.replace(",", ""))

        for i, property in enumerate(properties):

            # append link
            property_info = property.find("a", class_="propertyCard-link")
            link = "https://www.rightmove.co.uk" + property_info.attrs["href"]
            property_links.append(link)

        index += RESULTS_PER_PAGE
        if index >= number_of_listings:
            return property_links
        
        time.sleep(random.randint(1, 3))


def scrape_image(link,tag):
    # Downloads an image from the link and saves with the tag prefix

    res = requests.get(link, stream = True)

    #Generate a filename for the epc image
    filename = tag + link.split("/")[-1]

    if res.status_code == 200:
        try:
            with open(filename,'wb') as f:
                shutil.copyfileobj(res.raw, f)
            logging.info(f'Image sucessfully Downloaded: {filename}')
        except Exception as e:
            logging.error('Error at %s', 'division', exc_info=e)

    else:
        print('Image Couldn\'t be retrieved')


def scrape_link_info(link):
    # Scrapes relevant property info from rightmove link and returns a dict.
    
    logger.info(f"Extracting information from {link}")
    
    # request our page
    response = requests.get(link, headers=MY_HEADERS)

    # check status
    response.raise_for_status()    
    logger.debug(f"Response status: {response.status_code}")

    soup = BeautifulSoup(response.text, "html.parser")    
    page_info = soup.find(string=re.compile("window.PAGE_MODEL"))

    # remove javascript fluff from dict inside script
    jsonStr = re.search(r'\{.*\}', str(page_info)).group()
    page_dict = json.loads(jsonStr)

    # Print keys and values of the property data
    verbose_mode = False
    if verbose_mode == True:
        for k in page_dict.keys():
        
            try:
                for k2 in page_dict[k].keys():
                    print("\n -------------- \n")
                    print(k,k2,"\n")
                    print(page_dict[k][k2])
            except:
                pass
        

    property_dict = page_dict["propertyData"]
    property_id = property_dict['id']
    property_type = property_dict["propertySubType"]
    
    price = re.sub(r'\W+', '', property_dict['prices']['primaryPrice'])
    num_bedrooms = property_dict['bedrooms']
    num_bathrooms = property_dict['bathrooms']

    listingStr = property_dict["listingHistory"]["listingUpdateReason"].split(" ")
    listedData = listingStr[-1]
    if listedData == "yesterday":
        listedData = (datetime.now() - timedelta(1)).strftime('%d/%m/%Y')
    listedReason = listingStr[0]

    status = property_dict['status']
    description = property_dict['text']['description']
    description = re.sub(r"\<.*?\>"," ",description,0, re.UNICODE)
    
    short_description = property_dict['text']['shortDescription']
    share_description = property_dict['text']['shareDescription']

    #logger.info(description)
    #logger.info(short_description)
    #logger.info(share_description)
    
    address = property_dict['address']['displayAddress']
    
    postcode = property_dict['address']['outcode'] + " " + property_dict['address']['incode']
    nearest_stations = [(station['name'], station['distance']) for station in property_dict['nearestStations']]

    freehold = (page_dict["propertyData"]['tenure']['tenureType']=="FREEHOLD")
    leaseremaining = page_dict["propertyData"]['tenure']['yearsRemainingOnLease']
    
    agent = page_dict["analyticsInfo"]["analyticsBranch"]["brandName"]

    # Find garden details from the targeting list (bit cryptic)
    targeting_list = property_dict["dfpAdInfo"]["targeting"]

    # Determine if garden is a feature in the targeting list
    feature_tmp = [ tmp_dict['value'] for tmp_dict in property_dict["dfpAdInfo"]["targeting"] if tmp_dict['key'] == "F" ][0]
    hasGardenfeature = ("garden" in feature_tmp)

    # Regex the Tax band    
    reTax = r"[Tt]ax.*?[\s:\W][A-H][\W]"
    taxMatch = re.search(reTax, description, re.UNICODE)
    taxBand = None
    if taxMatch is not None:
        taxBand = taxMatch.group()[-2]

    # Regex the EPC rating
    reEPC = r"(([Ee][Nn][Ee][Rr][Gg][Yy]\s\w\w)|([Ee][Pp][Cc])).*?[\s:\W][A-H][\W]"
    EPCMatch = re.search(reEPC, description, re.UNICODE)
    EPCest = None
    if EPCMatch is not None:
        EPCest = EPCMatch.group()[-2]

    # Find EPC details
    hasEPCimage = False
    EPCUrl = None
    if property_dict["epcGraphs"] != []:
        hasEPCimage = True
        EPCUrl = property_dict["epcGraphs"][0]["url"]
        if False:
            scrape_image(EPCUrl,"EPC_")

    # Find floorplan details    
    floorplan = False
    floorplanURL = None
    if property_dict["floorplans"] != []:
        floorplan = True
        floorplanURL = property_dict["floorplans"][0]["url"]

    # Find image urls

    # Find virtual tour link
    virtualtour = False
    virtualtourURL = None
    if property_dict["virtualTours"] != []:
        virtualtour = False
        virtualtourURL = property_dict["virtualTours"][0]["url"]
    
    isAuction = page_dict["analyticsInfo"]["analyticsProperty"]["auctionOnly"]

    info = {"Link": link,
            "Listing change reason": listedReason,
            "Listing date": listedData,
            "Price": price,
            "Description": description,
            "Short Description": share_description,
            "Bedrooms": num_bedrooms,
            "Bathrooms": num_bathrooms,
            "Property Type" : property_type,
            "Address": address,
            "Postcode": postcode,
            "Garden": hasGardenfeature,
            "Floorplan": floorplan,
            "Floorplan URL": floorplanURL,
            "EPC rating est": EPCest,
            "EPC Image" : hasEPCimage,
            "EPC URL" : EPCUrl,
            "Tax Band": taxBand,
            "Freehold": freehold,
            "Lease Remaining": leaseremaining,
            'Nearest Stations': nearest_stations,
            "Agent": agent,
            "Auction": isAuction,
            }
    
    return info

def main():

    max_price = 400000
    min_price = 100000
    min_bedrooms = 2


    search_str = "".join(["https://www.rightmove.co.uk/property-for-sale/find.html?sortType=6",
                f"&minBedrooms={min_bedrooms}",
                f"&maxPrice={max_price}",
                f"&minPrice={min_price}",
                "&propertyTypes=detached%2Csemi-detached%2Cterraced",
                "&includeSSTC=false",
                "&mustHave=garden",
                "&dontShow=newHome%2Cretirement%2CsharedOwnership%2Cauction",
                "&locationIdentifier=REGION%"])
    
    # Scrape the property links    
    linkdf = scrape_links_across_boroughs(search_str,BOROUGHS)

    # Extract information from each scraped link
    link_infos = [None,]*len(linkdf)
    for i, link in enumerate(linkdf["Links"]):
        
        logger.info(f"Property {i}")
        info = scrape_link_info(link)
        link_infos[i] = info
        
    
    # Save to csv file named according to current time.
    timestr = time.strftime("%Y-%m-%d_%H-%M")
    filename = "search_result_" + timestr + ".csv"
    df = pd.DataFrame(link_infos)
    df.to_csv(filename, encoding="utf-8", header="true", index=False)



if __name__ == "__main__":
    main()