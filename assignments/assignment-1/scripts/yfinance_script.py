import yfinance
import pandas as pd

#define a list of sectors to scan
sectors = ["consumer-cyclical"]

sponsor_stocks = {
    # **Sports Gear & Apparel Sponsors**
    "NKE": "Nike Inc.",  # Sports gear, former official partner for many cricket teams
    "ADDYY": "Adidas AG",  # Adidas also sponsors major cricket events, kit sponsor of India
    "PUMSY": "Puma SE",  # Puma sponsors cricket teams and players
    "UA": "Under Armour, Inc.",  # Sportswear brand with involvement in cricket sponsorships

    # **Beverages & Food Sponsors**
    "PEP": "PepsiCo, Inc.",  # Long-time sponsor of Pakistan cricket
    "KO": "The Coca-Cola Company",  # ICC partner and major sponsor in cricket tournaments
    "BUD": "Anheuser-Busch InBev",  # Involved in global sports sponsorships
    "NSRGY": "Nestlé S.A.",  # Sponsors various cricket tournaments

    # **Banking & Financial Services Sponsors**
    "AXISBANK.NS": "Axis Bank",  # Indian financial institution sponsoring cricket events
    "HDB": "HDFC Bank Ltd.",  # Major bank in India, involved in sponsorships
    "ICICIBANK.NS": "ICICI Bank Ltd.",  # Indian bank sponsoring cricket events
    "JPM": "JPMorgan Chase & Co.",  # Global financial services company with sports sponsorships

    # **Airline & Travel Sponsors**
    "UAL": "United Airlines Holdings Inc.",  # Airlines often sponsor cricket tournaments
    "QATAR.OL": "Qatar Airways",  # Airline partner in international cricket
    "EMIRATES.DU": "Emirates Airline",  # Official ICC sponsor

    # **Energy & Industrial Sponsors**
    "XOM": "Exxon Mobil Corp.",  # Involved in sports sponsorships
    "SHEL": "Shell PLC",  # Energy company with sports sponsorship ties
    "TATAMOTORS.NS": "Tata Motors",  # IPL and cricket event sponsor
    # **Saudi Aramco is an ICC global sponsor but not publicly traded**

    # **Technology & Telecom Sponsors**
    "AAPL": "Apple Inc.",  # Involved in sports marketing and sponsorships
    "GOOGL": "Alphabet Inc. (Google)",  # YouTube and Google are ICC digital partners
    "META": "Meta Platforms, Inc.",  # Facebook, Instagram support cricket content
    "TCEHY": "Tencent Holdings Ltd.",  # Involved in esports and sports sponsorships
    "JIO.NS": "Reliance Jio",  # Indian telecom giant sponsoring IPL and cricket
    "VOD": "Vodafone Group Plc",  # Former cricket sponsor

    # **Media & Entertainment Sponsors**
    "DIS": "The Walt Disney Company",  # Parent company of Star Sports, cricket broadcaster
    "NFLX": "Netflix, Inc.",  # Producing cricket documentaries and streaming sports content

    # **Betting & Gaming Sponsors**
    "DRAFT": "DraftKings Inc.",  # Online sports betting company
    "RSI": "Rush Street Interactive",  # Betting-related stock
}


#this function returns a list of dictionaries for each ETF
def getTopETFSbySector(sector):
    top_etfs = {}
    for sector in sectors:
        top_etfs = yfinance.Sector(sector).top_etfs
    return top_etfs

#grab top etfs for all defined sectors
topetfs = getTopETFSbySector(sectors)
#merge topetfs and sponsor stocks
topetfs = {**topetfs, **sponsor_stocks}
print("TOP ETFS IS WOROKING: ", topetfs)

def saveTickerData(etfs):
    #assuming tickers being received as a dictionary.
    all_data = pd.DataFrame()

    for ticker, description in etfs.items():
        try:
            stock = yfinance.Ticker(ticker)
            hist = stock.history(period='2y')  # Fetch last 2 years of data
            
            if hist.empty:
                print(f"No data for {ticker}. Skipping")
                continue

            #fetch additional stock info
            info = stock.info
            sector = info.get("sector", "N/A")
            
            hist['Ticker'] = ticker  # Add a column for the ticker symbol
            hist['Date'] = hist.index
            hist['Sector'] = sector
            hist['Description'] = description

            all_data = pd.concat([all_data, hist])
        except Exception as e:
            print(f"Error fetching data for {ticker}: {e}")

    if not all_data.empty:
        all_data.to_csv('yfinance.csv', index=False)  # Save to a single CSV file
        print("Data saved successfully")
    else:
        print("No data was collected. check ETF symbols")

#save top etfs data to csv
saveTickerData(topetfs)