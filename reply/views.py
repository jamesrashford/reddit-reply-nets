from django.shortcuts import render
from django.http import JsonResponse

import praw
import prawcore

import networkx as nx


# Create your views here.
def index(request):
    subreddit_name = request.GET.get('subreddit', None)
    sort = request.GET.get('sort', 'hot')
    time = request.GET.get('time_filter', 'all')
    limit = 25

    if subreddit_name is not None:
        if subreddit_name[:2] == "r/":
            subreddit_name = subreddit_name[2:]

        reddit = praw.Reddit(client_id='YOUR_ID',
                     client_secret='YOUR_SECRET',
                     user_agent='YOUR_USERNAME')

        exists = True
        try:
            reddit.subreddits.search_by_name(subreddit_name, exact=True)
        except prawcore.exceptions.NotFound:
            exists = False

        if exists:
            subreddit = reddit.subreddit(subreddit_name)
            submissions = []

            if sort == "hot":
                submissions = subreddit.hot(limit=limit)
            elif sort == "new":
                submissions = subreddit.new(limit=limit)
            elif sort == "top":
                submissions = subreddit.top(limit=limit, time_filter=time)
            elif sort == "controversial":
                submissions = subreddit.controversial(limit=limit, time_filter=time)
            else:
                submissions = subreddit.hot(limit=limit)

        return render(request, 'index.html', {'subreddit_exists': exists, 'subreddit': subreddit, 'submissions': submissions, 'sort': sort, 'time': time})

    return render(request, 'index.html')

def reply_network(request):
    submission_id = request.GET.get('id', None)

    reddit = praw.Reddit(client_id='96FiEBP_GWtZ7Q',
                 client_secret='Qdbz2VblfixXJxwuReekx7XHDiE',
                 user_agent='research_node')

    submission = reddit.submission(id=submission_id)

    return render(request, 'reply_network.html', {'submission_id': submission_id, 'submission': submission})


def subswitch(request):
    username = request.GET.get('username', None)
    return render(request, 'subswitch.html', {'username': username})

def get_graph(request):
    submission_id = request.GET.get('id', None)

    reddit = praw.Reddit(client_id='YOUR_ID',
                 client_secret='YOUR_SECRET',
                 user_agent='YOUR_USERNAME')

    submission = reddit.submission(id=submission_id)

    comment_queue = []

    try:
        submission.comments.replace_more(limit=None)
    except prawcore.exceptions.TooLarge:
        print("Too Large. Skipping!")
        return None
    else:
        submission.comments.replace_more(limit=None)
        comment_queue = submission.comments[:]

    G = nx.DiGraph()

    total = 0

    while comment_queue:
        comment = comment_queue.pop(0)

        if not comment.author:
            continue

        if not comment.parent().author:
            continue

        u1 = comment.author.name
        u2 = comment.parent().author.name

        if u1 == u2:
            continue

        if u1 not in G.nodes():
            G.add_node(u1)

        if u2 not in G.nodes():
            G.add_node(u2)

        if not G.has_edge(u1, u2):
            G.add_edge(u1, u2, weight=0, meta=[])

        G[u1][u2]['weight'] += 1
        G[u1][u2]['meta'].append({
            "score": comment.score,
            "edited": comment.edited,
            "created_utc": comment.created_utc
        })

        comment_queue.extend(comment.replies)
        expand = len(comment.replies)
        total += expand

    return JsonResponse(nx.node_link_data(G), safe=False)


def get_switch_graph(request):
    username = request.GET.get('username', None)

    reddit = praw.Reddit(client_id='YOUR_ID',
                 client_secret='YOUR_SECRET',
                 user_agent='YOUR_USERNAME')

    if 'u/' in username:
        username = username[2:]

    user = reddit.redditor(name=username)

    if hasattr(user, 'is_suspended'):
        if user.is_suspended:
            return None

    G = nx.DiGraph()

    prev = None
    prev_time = None

    subs = user.new(limit=None)

    for submission in subs:
        name = submission.subreddit.display_name

        if name not in G.nodes():
            G.add_node(name)
            G.node[name]['post_data'] = []

        data_item = {}
        data_item['created_at'] = submission.created
        data_item['distinguished'] = submission.distinguished
        data_item['type'] = str(submission.__class__.__name__.lower())
        data_item['score'] = submission.score
        data_item['id'] = submission.id

        G.node[name]['post_data'].append(data_item)

        if prev:
            if prev not in G.nodes():
                G.add_node(prev)

            if not G.has_edge(name, prev):
                G.add_edge(name, prev, time_delta=[], count=0)

            G[name][prev]['time_delta'].append(prev_time - submission.created)
            G[name][prev]['count'] += 1

        prev = name
        prev_time = submission.created

    G.remove_edges_from(G.selfloop_edges())

    return JsonResponse(nx.node_link_data(G), safe=False)
