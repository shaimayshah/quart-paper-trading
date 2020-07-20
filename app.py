import quart.flask_patch
from quart import Quart, render_template, request, redirect, Response
from flask_sqlalchemy import SQLAlchemy
import os
import json 
import asyncio
from get_data import scrape_news, get_company_data, plot_historical, get_batch_data
from sentiment import get_sentiment_number

app = Quart(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data/trader.db'
db = SQLAlchemy(app)

class Money(db.Model):
    __tablename__ = "money"
    id = db.Column(db.Integer, primary_key=True)
    CurrCash = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return 'Money made' + str(self.id)

class Trade(db.Model):
    __tablename__ = "trade"
    trade_id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), nullable=False)
    action = db.Column(db.String(4), nullable=False)
    shares = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float(10), nullable=False)

    def __repr__(self):
        return 'Trade made ' + str(self.trade_id)

class Portfolio(db.Model):
    __tablename__ = "portfolio"
    ticker = db.Column(db.String(10), primary_key=True)
    shares = db.Column(db.Integer, nullable=False)
    avg_value = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return 'New stock added ' + self.ticker


ticker='AMZN'

@app.route('/', methods=['GET', 'POST'])
async def root():
    if request.method=='GET':
        return await render_template('index.html')
    elif request.method=='POST': 
        tick = (await request.form).to_dict()
        return redirect('/trade/'+tick['tick'])


@app.route('/trade/<string:ticker>', methods=['GET', 'POST'])
async def trade(ticker): 
    max_shares = 0
    avg_price = 0
    if request.method=='GET':
        sentiment_news = await scrape_news(ticker)
        name, price, market, isOpen = get_company_data(ticker)
        image = plot_historical(ticker)
        CurrCash = Money.query.filter_by(id=1).first().CurrCash
        if(Portfolio.query.filter_by(ticker=ticker).count() != 0):
            max_shares = Portfolio.query.filter_by(ticker=ticker)[0].shares
            avg_price = Portfolio.query.filter_by(ticker=ticker)[0].avg_value
        return await render_template('trade.html', sentiment=sentiment_news, name=name, price=price, 
        market=market, isOpen = isOpen, ticker=ticker, avg_price=avg_price, image=image, CurrCash=CurrCash, maxshares=int(max_shares))

    elif request.method == "POST":
            tick = (await request.form).to_dict()
            return redirect('/trade/'+tick['tick'])

@app.route('/search', methods=['GET', 'POST'])
async def search(): 
    if request.method == 'GET':
        return await render_template('search.html')
    else: 
        ticker = (await request.form).to_dict()
        return redirect('/trade/'+ticker['tick'])


@app.route('/trade/<string:ticker>/buy/<float:price>', methods=['GET', 'POST'])
async def buy(ticker, price):
    # First check how much money needed. 
    req = (await request.form).to_dict()
    share = req['shares']
    total_investment = price*int(share)
    CurrCash = Money.query.filter_by(id=1).first().CurrCash
    if(total_investment > CurrCash):
        return("Investment exceeds the amount of cash at hand.")
    else:
        # Reduce money availale 
        Money.query.filter_by(id=1).first().CurrCash = CurrCash - total_investment
        db.session.commit()
        # Make a transaction
        transac = Trade(ticker=ticker, action='buy', shares=share, price=price)
        db.session.add(transac)
        # Check to see if ticker in porfolio, if yes then: 
        if(Portfolio.query.filter_by(ticker=ticker).count() != 0):
            portfolio = Portfolio.query.filter_by(ticker=ticker)[0]
            curr_investment = portfolio.shares * portfolio.avg_value
            new_investment = total_investment
            new_total = curr_investment + new_investment
            total_shares = portfolio.shares + int(share)
            portfolio.shares = total_shares
            portfolio.avg_value = new_total/total_shares
            db.session.commit()

        else:
            portfolio = Portfolio(ticker=ticker, shares=share, avg_value=price)   
            db.session.add(portfolio)
            db.session.commit()      
        return redirect('/trade/'+ticker)

@app.route('/trade/<string:ticker>/sell/<float:price>', methods=['GET', 'POST'])
async def sell(ticker, price):
    req = (await request.form).to_dict()
    share = req['shares']
    total_sold = price*int(share)
    
    money = Money.query.filter_by(id=1).first()
    money.CurrCash += total_sold

    # Create a trade class
    transac = Trade(ticker=ticker, action='sell', shares=share, price=price)
    db.session.add(transac)

    #Edit Portfolio
    portfolio = Portfolio.query.filter_by(ticker=ticker)[0]
    new_shares = portfolio.shares - int(share)

    if(new_shares == 0):
        db.session.delete(portfolio)
        db.session.commit()
        return redirect('/trade/'+ticker)
    else: 
        portfolio.shares = new_shares
        db.session.commit()
        return redirect('/trade/'+ticker)

@app.route('/portfolio', methods=['GET', 'POST'])
def show_portfolio():
    portfolios = Portfolio.query.all()
    c = Portfolio.query.filter_by().count()
    money = Money.query.all()[0].CurrCash
    current_value = 0
    tickers = []
    if c == 0: 
        return render_template('portfolio.html', count = c)
    elif c == 1: 
        portfolios = Portfolio.query.all()[0]
        tickers.append(portfolios.ticker)
        prices = get_batch_data(tickers)
        current_value += prices * portfolios.shares
        return render_template('portfolio.html', portfolios = portfolios, prices = prices, money=money, currval = current_value, count = c)
    else:
        for porfolio in portfolios: 
            tickers.append(porfolio.ticker)
        prices = get_batch_data(tickers)
        for portfolio in portfolios:
            current_value += (prices[portfolio.ticker]*porfolio.shares)
        return render_template('portfolio.html', portfolios = portfolios, prices = prices, money=money, currval = current_value, count = c)

if __name__ == "__main__":
    os.environ["IEX_API_VERSION"] = "iexcloud-sandbox" 
    app.run(debug=True)



# @app.route('/news', methods=['GET', 'POST'])
# async def news():
#     sentiment = await scrape_news(ticker)
#     return sentiment

# @app.route('/trial', methods=['GET', 'POST'])
# def trial():
#     ticker = 'AMZN'
#     name, price, market, isOpen = get_company_data(ticker)
#     return(name)
