# encoding: utf-8
import io
import json
import sys
import threading
import traceback

from client import Pica
from util import *

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf8')


# only_latest: true增量下载    false全量下载
def download_comic(comic, only_latest):
    cid = comic["_id"]
    title = comic["title"]
    author = comic["author"]
    categories = comic["categories"]
    episodes = p.episodes_all(cid)
    # 增量更新
    if only_latest:
        episodes = filter_comics(comic, episodes)
    if episodes:
        print('%s | %s | %s | %s | %s:downloading---------------------' % (cid, title, author, categories,only_latest))
    else:
        return

    pics = []
    for eid in episodes:
        page = 1
        while True:
            docs = json.loads(p.picture(cid, eid["order"], page).content)["data"]["pages"]["docs"]
            page += 1
            if docs:
                pics.extend(list(map(lambda i: i['media']['fileServer'] + '/static/' + i['media']['path'], docs)))
            else:
                break

    # todo pica服务器抽风了,没返回图片回来,有知道原因的大佬麻烦联系下我
    if not pics:
        return

    path = './comics/' + convert_file_name(title) + '/'
    if not os.path.exists(path):
        os.makedirs(path)
    pics_part = list_partition(pics, int(get_cfg('crawl', 'concurrency')))
    for part in pics_part:
        threads = []
        for pic in part:
            t = threading.Thread(target=download, args=(p, title, pics.index(pic), pic))
            threads.append(t)
            t.start()
        for t in threads:
            t.join()
        last = pics.index(part[-1]) + 1
        print("downloaded:%d,total:%d,progress:%s%%" % (last, len(pics), int(last / len(pics) * 100)))
    # 记录已下载过的id
    f = open('./downloaded.txt', 'ab')
    f.write((str(cid) + '\n').encode())
    f.close()


p = Pica()
p.login()
p.punch_in()

# 排行榜/收藏夹的漫画
# comics = p.leaderboard()
comics = []

# # 关键词订阅的漫画
keywords = os.environ["SUBSCRIBE_KEYWORD"].split(',')
for keyword in keywords:
    subscribe_comics = p.search_all(keyword)
    print('关键词%s : 订阅了%d本漫画' % (keyword, len(subscribe_comics)))
    comics += subscribe_comics

# 收藏先不下
# favourites = p.my_favourite()
favourites = []
print('id | 本子 | 画师 | 分区')

for comic in favourites + comics:
    try:
        # 收藏夹:全量下载  其余:增量下载
        download_comic(comic, comic not in favourites)
        info = p.comic_info(comic['_id'])
        if info["data"]['comic']['isFavourite']:
            p.favourite(comic["_id"])
    except:
        print('download failed,{},{},{}', comic['_id'], comic["title"], traceback.format_exc())
        continue

# 记录上次运行时间
f = open('./run_time_history.txt', 'ab')
f.write((str(datetime.strftime(datetime.now(),'%Y-%m-%d %H:%M:%S')) + '\n').encode())
f.close()
