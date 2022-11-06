"""This code was written by
        Eva Batelaan <batelaan@stanford.edu>
        Thomas Brink <tbrink@stanford.edu>
        Michelle Lahrkamp <ml17270@stanford.edu>
    Assignment 2 Group 3

    Searches through tweets collected by download_tweets.py to find all replies.
    Collects reply tweets from Twitter streaming API via tweepy and prints them.

    Use:
    python3 download_reply_tweets.py > congress_df_YYYY-MM-DD_reply_tweets.txt

    The following flags are required:
        --keyfile: twitter API credentials file
            ex: cred.txt
        --initial_tweets: txt of output generated by download_tweets.py
            ex: congress_df_YYYY-MM-DD_tweets.txt

    Note:
    YYYY-MM-DD should match the YYYY-MM-DD in the name of the initial_tweets file
"""
import argparse
import datetime
import numpy as np
import sys
import json
from tweepy import Stream, Client, StreamingClient, StreamRule, Paginator


def eprint(*args, **kwargs):
    """Print to stderr"""
    print(*args, file=sys.stderr, **kwargs)


class CustomStreamingClient(StreamingClient):
    """Extracted from tweet_stream.py provided in assignment 1"""
    total_tweets = 0
    sunset_time = datetime.datetime.now()

    def __init__(self, write=print, **kwds):
        super(CustomStreamingClient, self).__init__(**kwds)
        self.write = write

    def on_tweet(self, tweet):
        self.write(tweet.data)

    def on_data(self, raw_data):
        self.write(raw_data)
        self.total_tweets += 1

    def on_error(self, status_code):
        eprint(status_code)


def retrieve_reply_tweets(line: str):
    """Query recent tweets in the conversation and print each individually
    """
    og_tweet = json.loads(line)
    conversation_id_str = "conversation_id:" + \
        str(og_tweet['tweet_info']['conversation_id'])
    count = og_tweet['tweet_info']['public_metrics']['reply_count']
    eprint("Getting reply tweets for " + conversation_id_str + " estimated replies: " + str(count))

     # Run query to get tweets. Impose no limits to make sure full conversations are extracted
    try:
        paginator = Paginator(twitter_client.search_recent_tweets,
                              query=conversation_id_str,
                              expansions=[
                                  'author_id', 'entities.mentions.username', 'in_reply_to_user_id'],
                              tweet_fields=['conversation_id',
                                            'created_at', 'public_metrics', 'in_reply_to_user_id'],
                              user_fields=['public_metrics', 'verified'],
                              max_results=100)
        # Extract user information and print each flattened tweet as a json
        includes = {}
        for response in paginator:
            includes = response.includes['users'][0].data if 'users' in response.includes.keys() else {}
            break
        for tweet in paginator.flatten():
            full_object = {}
            full_object['user_info'] = includes
            full_object['tweet_info'] = tweet.data
            print(json.dumps(full_object))

    except KeyboardInterrupt:
        eprint()
    except AttributeError:
        # Catch rare occasion when Streaming API returns None
        pass
    pass


if __name__ == "__main__":
    # Set up the argument parser
    parser = argparse.ArgumentParser(
        description="Fetch data with Twitter Streaming API"
    )
    parser.add_argument(
        "--keyfile", help="file with user credentials", required=True)
    parser.add_argument(
        "--initial_tweets", help="file with initial tweets", required=True)
    flags = parser.parse_args()

    # Read twitter app credentials and set up authentication
    creds = {}
    for line in open(flags.keyfile, "r"):
        row = line.strip()
        if row:
            key, value = row.split()
            creds[key] = value

    twitterstream = Stream(
        creds["api_key"], creds["api_secret"], creds["token"], creds["token_secret"]
    )

    # Track time and start streaming
    starttime = datetime.datetime.now()
    twitter_streaming_client = CustomStreamingClient(
        write=print, bearer_token=creds["bearer_token"])
    twitter_client = Client(
        bearer_token=creds["bearer_token"], wait_on_rate_limit=True)

    # Clear out old rules
    old_rules = twitter_streaming_client.get_rules()
    if old_rules.data is not None:
        rule_ids = [rule.id for rule in old_rules.data]
        twitter_streaming_client.delete_rules(rule_ids)

    # Start streaming
    eprint("Started running at", starttime)
    i = 1
    prob_sample = 0.3
    for line in open(flags.initial_tweets, "r"):
        # Randomly sample 30% of the conversations to try to avoid pulling over
        # the developer limit
        if np.random.uniform() < prob_sample:
          retrieve_reply_tweets(line)
          eprint(i)
          i += 1
        else:
          continue

    eprint("total run time", datetime.datetime.now() - starttime)
