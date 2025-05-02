import streamlit as st
import yfinance as yf
import time
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

# Set the layout to wide mode
st.set_page_config(layout="wide")

# Title of the app
st.title("Stock Information Fetcher")

# Custom CSS to adjust the width of the number input box
st.markdown(
    """
    <style>
    .streamlit-expanderHeader {
        font-size: 20px;
    }
    .number-input {
        width: 150px;  /* Adjust this width as needed */
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Input section for contributions
st.header("Investment Contribution Setup")
contribution_frequency = st.radio("Contribution Frequency:", ("Weekly", "Biweekly"))
contribution_amount = st.number_input("Contribution Amount ($):", min_value=0.0, max_value=100000.0, step=0.01, format="%.2f", value=50.00)

# Calculate total contributions based on frequency
if contribution_frequency == "Weekly":
    total_contributions = contribution_amount * 52
else:
    total_contributions = contribution_amount * 26

# List of tickers
tickers = [
    "NEZYX", "VBTIX", "WTRIX", "BPRIX", "FIHBX", "FBNRX", 
    "FGBMX", "RIDGX", "CSRSX", "MEIJX", "SAPYX", "VIIIX", 
    "RGAGX", "NRSRX", "VASVX", "VMCIX", "JAENX", "GSSIX", 
    "VSCIX", "OTIIX", "AAERX", "VTSNX", "MIDJX", "VREMX",
    "TCIXX", "TISIX", "TIILX", "TBIIX", "TIBDX", "TIBFX",
    "TIHYX", "TILIX", "TILGX", "TILVX", "TISPX", "TISBX",
    "TIMVX", "VMGMX", "TIGRX", "TEQLX", "FGBMX", "FBNRX",
]

# Function to fetch stock data
def fetch_stock_data():
    results = {}
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            results[ticker] = info
        except Exception as e:
            results[ticker] = f"Error fetching data: {e}"
        
        time.sleep(0.5)
    return results

# Function to calculate price one year ago
def get_price_one_year_ago(ticker):
    stock = yf.Ticker(ticker)
    historical_data = stock.history(period='1y')
    
    price_one_year_ago = historical_data['Close'].iloc[0] if not historical_data.empty else None
    current_price = historical_data['Close'].iloc[-1] if not historical_data.empty else None
    return price_one_year_ago, current_price

# Fetch stock data automatically on app start
results = fetch_stock_data()

# Prepare DataFrame for ranking
data = []
for ticker, info in results.items():
    if isinstance(info, dict):
        longName = info.get('longName', 'N/A')
        yield_value = info.get('yield', 'N/A')
        dividend_rate = info.get('dividendRate', 'N/A')
        
        ytd_return = info.get('ytdReturn', 'N/A')
        if isinstance(ytd_return, (float, int)):
            ytd_return_display = f"{ytd_return:.2f}%"
        else:
            ytd_return_display = 'N/A'

        price_one_year_ago, current_price = get_price_one_year_ago(ticker)

        data.append({
            'Ticker': ticker,
            'Long Name': longName,
            'Yield': yield_value,
            'Dividend Rate': dividend_rate,
            'YTD Return': ytd_return_display,
            'Expense Ratio': info.get('annualReportExpenseRatio', 'N/A'),
            'Total Assets': info.get('totalAssets', 'N/A'),
            'Beta': info.get('beta3Year', 'N/A'),
            'Price One Year Ago': price_one_year_ago,
            'Current Price': current_price,
            'Closing Price': current_price
        })

# Create DataFrame
df = pd.DataFrame(data)

# Convert relevant columns to numeric
numeric_columns = ['Yield', 'Dividend Rate', 'Expense Ratio', 'Total Assets', 'Beta']
for col in numeric_columns:
    df[col] = pd.to_numeric(df[col], errors='coerce')

# Handle YTD Return for scoring
df['YTD Return Numeric'] = pd.to_numeric(df['YTD Return'].str.replace('%', ''), errors='coerce')

# Calculate ranking score
df['Score'] = (
    df['Yield'].fillna(0) * 0.25 + 
    df['Dividend Rate'].fillna(0) * 0.25 + 
    df['YTD Return Numeric'].fillna(0) * 0.25 - 
    df['Expense Ratio'].fillna(0) * 0.25 +
    (df['Total Assets'].fillna(0) / 1e6) * 0.1
)

# Rank stocks based on score
df['Rank'] = df['Score'].rank(ascending=False)

# Calculate investment distribution
if total_contributions > 0:
    total_score = df['Score'].sum()
    df['Investment Percentage'] = (df['Score'] / total_score) * 100
    
    if df['Investment Percentage'].sum() != 0:
        df['Investment Percentage'] = (df['Investment Percentage'] / df['Investment Percentage'].sum()) * 100

    df['Dollar Allocation'] = (df['Investment Percentage'] / 100) * contribution_amount

    under_1_percent = df[df['Dollar Allocation'] < 1]
    under_1_percent_total = under_1_percent['Dollar Allocation'].sum()
    
    above_1_percent = df[df['Dollar Allocation'] >= 1]
    
    pie_data = above_1_percent[['Long Name', 'Dollar Allocation']]
    
    if under_1_percent_total > 0:
        under_1_percent_data = pd.DataFrame({
            'Long Name': ['Stocks Under 1%'],
            'Dollar Allocation': [under_1_percent_total]
        })
        pie_data = pd.concat([pie_data, under_1_percent_data], ignore_index=True)

    plt.figure(figsize=(10, 6))
    plt.pie(pie_data['Dollar Allocation'], labels=pie_data['Long Name'], autopct='%1.1f%%', startangle=140, colors=plt.cm.tab20.colors)
    plt.title('Investment Allocation by Stock')
    st.pyplot(plt)

    suggested_investment_df = df[['Long Name', 'Ticker', 'Current Price', 'Investment Percentage', 'Dollar Allocation']]
    suggested_investment_df = suggested_investment_df.rename(columns={'Investment Percentage': 'Percentage Contribution'})
    suggested_investment_df['Dollar Allocation'] = suggested_investment_df['Dollar Allocation'].map('${:,.2f}'.format)

    st.write("### Suggested Investment Distribution")
    st.dataframe(suggested_investment_df)

    # Summary Report
    total_investment = suggested_investment_df['Percentage Contribution'].sum()
    num_investments = len(suggested_investment_df)
    average_allocation = suggested_investment_df['Percentage Contribution'].mean()

    top_performers = suggested_investment_df.nlargest(3, 'Percentage Contribution')
    underperformers = suggested_investment_df.nsmallest(3, 'Percentage Contribution')
    average_beta = df['Beta'].mean()

    st.subheader("Investment Summary Report")
    st.write(f"- **Total Investment Amount**: {total_investment:.2f}%")
    st.write(f"- **Number of Investments**: {num_investments}")
    st.write(f"- **Average Allocation**: {average_allocation:.2f}%")

    st.write("### Top Performers")
    st.table(top_performers)

    st.write("### Underperformers")
    st.table(underperformers)

    st.write(f"- **Average Beta**: {average_beta:.2f}")

# Display DataFrame above the stock info section
st.write("### Stock Rankings Based on Profitability Metrics")
st.dataframe(df[['Ticker', 'Long Name', 'Yield', 'Dividend Rate', 'YTD Return', 'Expense Ratio', 'Total Assets', 'Beta', 'Price One Year Ago', 'Current Price', 'Closing Price', 'Score', 'Rank']])

# Display results with profitability metrics
for ticker, info in results.items():
    if isinstance(info, dict):
        longName = info.get('longName', 'N/A')
        st.subheader(f"{longName} ({ticker})")
        
        yield_value = info.get('yield', 'N/A')
        dividend_rate = info.get('dividendRate', 'N/A')
        
        price_one_year_ago, current_price = get_price_one_year_ago(ticker)
        
        if price_one_year_ago is not None and current_price is not None:
            st.write(f"- **YTD Return**: {ytd_return_display} (if applicable)")
            st.write(f"- **Price One Year Ago**: ${price_one_year_ago:.2f}")
            st.write(f"- **Current Price**: ${current_price:.2f}")
            st.write(f"- **Closing Price**: ${current_price:.2f}")
        else:
            st.write("- **Price Information**: Not available")

        st.write(f"- **Expense Ratio**: {info.get('annualReportExpenseRatio', 'N/A'):.2%} (if applicable)")
        st.write(f"- **Total Assets**: ${info.get('totalAssets', 'N/A'):,} (if applicable)")
        
        beta = info.get('beta3Year', 'N/A')
        if beta != 'N/A':
            beta_display = f"{beta:.2f}"
        else:
            beta_display = "N/A"
        
        col1, col2 = st.columns([1, 2])
        with col1:
            # Add a unique key to the button
            if st.button(f"Show Beta: {beta_display}", key=f"beta_button_{ticker}", help="Beta is a measure of a stock's volatility in relation to the market. A beta of 1 indicates that the stock's price moves with the market, while a beta greater than 1 indicates greater volatility."):
                st.session_state.beta_clicked = True
                st.write(f"**Beta (3-Year)**: {beta_display} (if applicable)")

        with col2:
            st.write(f"**Beta (3-Year)**: {beta_display} (if applicable)")

        st.write(info)

    else:
        st.subheader(f"{ticker} - Error")
        st.write(info)

# Summary report should go here after the Suggested Investment Distribution DataFrame


# Display the count and total of stocks under 1% allocation
st.write(f"### {len(under_1_percent)} stocks under 1% allocation with total allocation of ${under_1_percent_total:.2f}")
