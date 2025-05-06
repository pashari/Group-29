import praw
import csv
from datetime import datetime
import pandas as pd

#creating instance of reddit
reddit = praw.Reddit(
    client_id="DTCULezwtWNnFgAXugHo0Q",
    client_secret="yeyPpO64BkqqvySYxKsuyGvU-5tRBQ",
    password="Behsiv-baxgy7-qefcaw",
    user_agent="AI601 Assignment 1 by u/Zardata",
    username="Zardata",
)
# print(reddit.read_only)
reddit.read_only = True

# #check if credentials are working
# subreddit = reddit.subreddit("politics")
# print(subreddit.description)

#fields to include: title, post text, author, date, upvotes, subreddit name
#write function to get top posts from a certain subreddit
def getTopPosts(no_of_posts, keywords):
    with open("praw.csv","w", newline="") as csvfile:
        fieldnames = ["Title", "Post Text","Submission URL", "Author", "Date Posted", "Upvotes", "Subreddit Name" ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for keyword in keywords:
            submissions = reddit.subreddit("all").search(
                keyword, 
                limit=no_of_posts, 
                sort="top"
            )
            for submission in submissions:
                #to check methods and properties of submission object
                # print(dir(submission))
                # print(str(submission.selftext.strip()))
                writer.writerow({
                        "Title": submission.title,
                        "Post Text": submission.selftext.strip(),
                        "Submission URL": submission.url,
                        "Author": str(submission.author),
                        "Date Posted": datetime.fromtimestamp(submission.created_utc).strftime("%Y-%m-%d %H:%M:%S"),
                        "Upvotes": submission.score,
                        "Subreddit Name": submission.subreddit.display_name,
                        
                })


getTopPosts(100, ["cricket", "Pakistan vs India match", "cricket betting trends", "T20 world cup", "Champions Trophy", "ICC World Cup", "cricket sponsorships"])

