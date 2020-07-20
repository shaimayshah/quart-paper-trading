from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
import pandas as pd

vader = SentimentIntensityAnalyzer()

def get_sentiment_number(news):
    columns = ['headline']
    news = pd.DataFrame(news, columns=columns)
    scores = news['headline'].apply(vader.polarity_scores).tolist()
    scores_df = pd.DataFrame(scores)
    news = news.join(scores_df, rsuffix='_right')

    return news['compound'].mean()


def get_sentiment(sentiment_num):
    if(sentiment_num < 0):
        if(sentiment_num > -0.5):
            return "Poor sentiment"
        else:
            return "Extremely poor sentiment"
    elif(sentiment_num > 0):
        if(sentiment_num < 0.5):
            return "Moderate sentiment"
        else:
            return "Extremely good sentiment"
