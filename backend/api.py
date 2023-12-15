import asyncio
import concurrent.futures
from aioflask import Flask, jsonify, Response # flask must be version == 2.1.3
import covalent as ct
from rake_nltk import Rake
from threading import Lock
from predict import get_sentiment
from scraping.scrape import scrape_page
import time
import uuid

rake_lock = Lock()
process_pool = concurrent.futures.ProcessPoolExecutor()
thread_pool = concurrent.futures.ThreadPoolExecutor()

def update_keyword_score(keywords, scores):
    for keyword in keywords:
        if keyword[1] in scores:
            scores[keyword[1]][0] += 1#keyword[0]
        else:
            scores[keyword[1]] = [1, 0]#[keyword[0], 0]

def process_post(post):
    keyword_scores = {}
    rake_lock.acquire()
    rake = Rake()
    rake_lock.release()
    postData = post["postData"]
    to_analyze = ["" if postData["postContent"] == None else postData["postContent"]]

    # Title keywords and sentiment? Score seems important but sentiment seems silly because it will mostly
    # be positive?
    rake.extract_keywords_from_text(post["title"])
    keywords = rake.get_ranked_phrases_with_scores()
    update_keyword_score(keywords, keyword_scores)
    for keyword in keywords:
        keyword_scores[keyword[1]][1] += 1

    for comment in postData["comments"]:
        to_analyze.append(comment["comment"])
    sentiments = get_sentiment(to_analyze)
    if postData["postContent"] != None:
        rake.extract_keywords_from_text(postData["postContent"])
        keywords = rake.get_ranked_phrases_with_scores()
        update_keyword_score(keywords, keyword_scores)
        for keyword in keywords:
            keyword_scores[keyword[1]][1] += sentiments[0]
    for i in range(1, len(sentiments)):
        rake.extract_keywords_from_text(postData["comments"][i - 1]["comment"])
        keywords = rake.get_ranked_phrases_with_scores()
        update_keyword_score(keywords, keyword_scores)
        for keyword in keywords:
            keyword_scores[keyword[1]][1] += sentiments[i]
    return keyword_scores
    
def process_posts(posts):
    post_tasks = []
    keyword_scores = {}
    for post in posts:
        post_tasks.append(thread_pool.submit(process_post, post))
    for task in post_tasks:
        scores = task.result()
        for key in scores:
            if key in keyword_scores:
                keyword_scores[key][0] += scores[key][0]
                keyword_scores[key][1] += scores[key][1]
            else:
                keyword_scores[key] = [scores[key][0], scores[key][1]]
    return keyword_scores

def process_query(query):
    print("Getting data...")
    data = scrape_page(query, 10, thread_pool)

    print("Processing data...")
    keyword_scores = process_posts(data["posts"])

    items = list(keyword_scores.items())
    items.sort(key=lambda x: (x[1][0], x[1][0]))
    items.reverse()
    
    num_results = 100
    increment = 1 #len(items) // (num_results * 4) + 1
    final_output = []
    for i in range(num_results):
        elem = items[increment * i]
        final_output.append({
            "key": elem[0],
            "score": int(elem[1][0]),
            "sentiment": int(elem[1][1])
        })
    
    print("Done")
    return final_output

if __name__ == '__main__':
    app = Flask(__name__)

    queries = {}

    def purge_queries():
        to_delete = []
        for key in queries:
            if time.time() - queries[key][1] > 500: # 500 second max lifetim
                to_delete.append(key)
        for key in to_delete:
            queries[key][0].cancel()
            queries.pop(key)

    @app.route('/query/submit/<query>', methods=['GET'])
    async def submit_query(query):
        purge_queries()
        if len(queries) > 5:
            resp = Response(response="Request queue full", status=403)
        else:
            id = uuid.uuid4()
            loop = asyncio.get_running_loop()
            queries[str(id)] = (loop.run_in_executor(process_pool, process_query, query), time.time())
            resp = jsonify({ "id": id })
        #resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp

    @app.route('/query/status/<id>', methods=['GET'])
    async def get_query_status(id):
        if id not in queries:
            resp = Response(response="Invalid id", status=400)
        else:
            query = queries[id]
            if query[0].done():
                resp = jsonify({ "done": True, "data": query[0].result() })
            else:
                resp = jsonify({ "done": False })
        #resp.headers.add("Access-Control-Allow-Origin", "*")
        return resp

    app.run()